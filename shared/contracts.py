"""KALKI core contracts.

These dataclasses and enums are the *stable internal interfaces* of KALKI.
They are deliberately dependency-free (stdlib only) and JSON-serialisable so
they can cross every boundary in the system: planner -> orchestrator ->
tools -> memory -> API -> frontend.

Design rules (do not break without a version bump — see docs/CONTRACTS.md):
  * Every type has ``to_dict()`` / ``from_dict()`` for transport & storage.
  * Enums serialise to their ``str`` value.
  * New optional fields may be added; existing fields keep their meaning.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def new_id(prefix: str = "") -> str:
    """Short, sortable-ish unique id."""
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}-{raw}" if prefix else raw


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _StrEnum(str, Enum):
    """Enum whose members are also their string values (JSON friendly)."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────
class TaskStatus(_StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class ExecutionStatus(_StrEnum):
    """Terminal (and awaiting) states of a whole objective."""

    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"


class RiskLevel(_StrEnum):
    SAFE = "safe"
    ELEVATED = "elevated"
    DANGEROUS = "dangerous"


class FailureClass(_StrEnum):
    """How a tool/step failure is categorised by the recovery engine."""

    TRANSIENT = "transient"        # retry may succeed (network, flaky test)
    TOOL_ERROR = "tool_error"      # tool misused / bad args -> fix & retry
    LOGIC_ERROR = "logic_error"    # the change/approach is wrong -> replan
    PERMISSION = "permission"      # blocked pending human approval
    FATAL = "fatal"                # unrecoverable -> fail the objective
    UNKNOWN = "unknown"


class MemoryScope(_StrEnum):
    SESSION = "session"        # current run: objective, plan, tool calls, errors
    PROJECT = "project"        # per-repository knowledge
    LONG_TERM = "long_term"    # cross-project engineering experience (vectors)


class EventType(_StrEnum):
    """Observable execution events streamed to the frontend."""

    PLAN_CREATED = "PLAN_CREATED"
    PLAN_REVISED = "PLAN_REVISED"
    TASK_STARTED = "TASK_STARTED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    MEMORY_RETRIEVED = "MEMORY_RETRIEVED"
    MEMORY_STORED = "MEMORY_STORED"
    CODE_CHANGED = "CODE_CHANGED"
    TEST_STARTED = "TEST_STARTED"
    TEST_FAILED = "TEST_FAILED"
    TEST_PASSED = "TEST_PASSED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    DEPLOY_STARTED = "DEPLOY_STARTED"
    DEPLOY_COMPLETED = "DEPLOY_COMPLETED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    OBJECTIVE_COMPLETED = "OBJECTIVE_COMPLETED"
    OBJECTIVE_FAILED = "OBJECTIVE_FAILED"
    LOG = "LOG"


# ─────────────────────────────────────────────────────────────
# Task & Plan
# ─────────────────────────────────────────────────────────────
@dataclass
class Task:
    """A single unit of work in a plan."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    tool: Optional[str] = None                 # suggested tool name
    tool_args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    attempts: int = 0
    result: Optional["ToolResult"] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["result"] = self.result.to_dict() if self.result else None
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Task":
        res = d.get("result")
        return cls(
            id=d["id"],
            description=d["description"],
            status=TaskStatus(d.get("status", "pending")),
            tool=d.get("tool"),
            tool_args=d.get("tool_args", {}) or {},
            depends_on=d.get("depends_on", []) or [],
            attempts=d.get("attempts", 0),
            result=ToolResult.from_dict(res) if res else None,
            error=d.get("error"),
            metadata=d.get("metadata", {}) or {},
        )


@dataclass
class Plan:
    """An ordered, mutable set of tasks for one objective."""

    objective: str
    tasks: list[Task] = field(default_factory=list)
    revision: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # -- queries -------------------------------------------------
    def get(self, task_id: str) -> Optional[Task]:
        return next((t for t in self.tasks if t.id == task_id), None)

    def next_task(self) -> Optional[Task]:
        """First pending task whose dependencies are all completed."""
        done = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        for t in self.tasks:
            if t.status != TaskStatus.PENDING:
                continue
            if all(dep in done for dep in t.depends_on):
                return t
        return None

    def is_complete(self) -> bool:
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)
            for t in self.tasks
        )

    def has_failure(self) -> bool:
        return any(t.status == TaskStatus.FAILED for t in self.tasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "revision": self.revision,
            "metadata": self.metadata,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Plan":
        return cls(
            objective=d["objective"],
            revision=d.get("revision", 0),
            metadata=d.get("metadata", {}) or {},
            tasks=[Task.from_dict(t) for t in d.get("tasks", [])],
        )


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────
@dataclass
class ToolSpec:
    """Describes a tool so the planner/model can select it. Dev 3 authors
    tools by providing a spec + a callable (see agent.tools.base.Tool)."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)  # JSON-schema-ish
    risk: RiskLevel = RiskLevel.SAFE

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk"] = self.risk.value
        return d


@dataclass
class ToolResult:
    """The outcome of invoking a tool. Uniform across all tools."""

    ok: bool
    tool: str
    output: Any = None
    error: Optional[str] = None
    failure_class: Optional[FailureClass] = None
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, tool: str, output: Any = None, **meta: Any) -> "ToolResult":
        return cls(ok=True, tool=tool, output=output, metadata=meta)

    @classmethod
    def failure(
        cls,
        tool: str,
        error: str,
        failure_class: FailureClass = FailureClass.UNKNOWN,
        **meta: Any,
    ) -> "ToolResult":
        return cls(
            ok=False,
            tool=tool,
            error=error,
            failure_class=failure_class,
            metadata=meta,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["failure_class"] = self.failure_class.value if self.failure_class else None
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ToolResult":
        fc = d.get("failure_class")
        return cls(
            ok=d["ok"],
            tool=d["tool"],
            output=d.get("output"),
            error=d.get("error"),
            failure_class=FailureClass(fc) if fc else None,
            duration_ms=d.get("duration_ms", 0),
            metadata=d.get("metadata", {}) or {},
        )


# ─────────────────────────────────────────────────────────────
# Memory
# ─────────────────────────────────────────────────────────────
@dataclass
class MemoryRecord:
    """A single stored memory. ``embedding`` is optional; the store computes
    it when absent."""

    scope: MemoryScope
    content: str
    id: str = field(default_factory=lambda: new_id("mem"))
    user_id: Optional[str] = None
    project: Optional[str] = None
    session_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scope"] = self.scope.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MemoryRecord":
        return cls(
            scope=MemoryScope(d["scope"]),
            content=d["content"],
            id=d.get("id", new_id("mem")),
            user_id=d.get("user_id"),
            project=d.get("project"),
            session_id=d.get("session_id"),
            tags=d.get("tags", []) or [],
            metadata=d.get("metadata", {}) or {},
            embedding=d.get("embedding"),
            created_at=d.get("created_at", utcnow_iso()),
        )


@dataclass
class MemoryResult:
    """A retrieved memory plus its similarity score (0..1)."""

    record: MemoryRecord
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"record": self.record.to_dict(), "score": self.score}


# ─────────────────────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────────────────────
@dataclass
class AgentEvent:
    """An observable moment in an execution, streamed to consumers."""

    type: EventType
    task_id: str                       # objective/run id
    user_id: Optional[str] = None
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("evt"))
    seq: int = 0
    timestamp: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        return d


# ─────────────────────────────────────────────────────────────
# Agent state & result
# ─────────────────────────────────────────────────────────────
@dataclass
class AgentState:
    """The full persistent execution state of one objective. This is the
    single source of truth the orchestrator advances and memory persists —
    KALKI is explicitly NOT stateless."""

    objective: str
    id: str = field(default_factory=lambda: new_id("run"))
    user_id: Optional[str] = None
    project: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    node: str = "START"                       # current state-machine node
    plan: Optional[Plan] = None
    current_task_id: Optional[str] = None
    plan_revisions: int = 0
    events: list[AgentEvent] = field(default_factory=list)
    retrieved_memories: list[MemoryResult] = field(default_factory=list)
    scratch: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)

    def touch(self) -> None:
        self.updated_at = utcnow_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "objective": self.objective,
            "project": self.project,
            "status": self.status.value,
            "node": self.node,
            "plan": self.plan.to_dict() if self.plan else None,
            "current_task_id": self.current_task_id,
            "plan_revisions": self.plan_revisions,
            "events": [e.to_dict() for e in self.events],
            "retrieved_memories": [m.to_dict() for m in self.retrieved_memories],
            "scratch": self.scratch,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentState":
        st = cls(
            objective=d["objective"],
            id=d.get("id", new_id("run")),
            user_id=d.get("user_id"),
            project=d.get("project"),
            status=ExecutionStatus(d.get("status", "running")),
            node=d.get("node", "START"),
            plan=Plan.from_dict(d["plan"]) if d.get("plan") else None,
            current_task_id=d.get("current_task_id"),
            plan_revisions=d.get("plan_revisions", 0),
            scratch=d.get("scratch", {}) or {},
            error=d.get("error"),
            created_at=d.get("created_at", utcnow_iso()),
            updated_at=d.get("updated_at", utcnow_iso()),
        )
        return st


@dataclass
class ExecutionResult:
    """Terminal report returned by the orchestrator."""

    run_id: str
    objective: str
    status: ExecutionStatus
    plan: Optional[Plan] = None
    summary: str = ""
    verified: bool = False
    error: Optional[str] = None
    event_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "objective": self.objective,
            "status": self.status.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "summary": self.summary,
            "verified": self.verified,
            "error": self.error,
            "event_count": self.event_count,
            "metadata": self.metadata,
        }
