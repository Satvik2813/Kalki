"""KALKI orchestrator — the autonomous execution engine.

A deterministic state machine over :class:`AgentState`. It is explicitly NOT a
``prompt -> LLM -> response`` call: it maintains persistent execution state and
advances through named nodes, using tools, memory, recovery and verification.

    START
      -> UNDERSTAND_OBJECTIVE
      -> CREATE_PLAN
      -> SELECT_NEXT_TASK  <------------------+
      -> EXECUTE_TOOL                         |
      -> OBSERVE_RESULT                       |
      -> DECIDE_NEXT_ACTION --(retry/replan)--+
      -> VERIFY
      -> STORE_MEMORY
      -> END

Design note — LangGraph: the PRD names LangGraph as *preferred if it provides
clear value*. We implement an explicit, dependency-free state machine instead:
it keeps the core installable/testable offline, gives full control over the
recovery/replan edges, and serialises cleanly to :class:`AgentState`. The node
set maps 1:1 onto a LangGraph graph, so migrating later is mechanical. See
docs/AGENT_FLOW.md.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from agent.events import EventBus
from agent.permissions import PermissionManager
from agent.planner import Planner
from agent.recovery import ABORT, ESCALATE, REPLAN, RETRY, RecoveryEngine
from agent.tools.base import ToolContext, ToolRegistry
from agent.tools.builtins import register_builtins
from agent.verification import Verifier
from config.settings import Settings, get_settings
from memory.manager import MemoryManager
from models.base import ModelProvider
from models.registry import get_provider
from shared.contracts import (
    AgentState,
    EventType,
    ExecutionResult,
    ExecutionStatus,
    RiskLevel,
    Task,
    TaskStatus,
)

log = logging.getLogger("kalki.orchestrator")

# State-machine node names
START = "START"
UNDERSTAND = "UNDERSTAND_OBJECTIVE"
CREATE_PLAN = "CREATE_PLAN"
SELECT_NEXT = "SELECT_NEXT_TASK"
EXECUTE = "EXECUTE_TOOL"
OBSERVE = "OBSERVE_RESULT"
DECIDE = "DECIDE_NEXT_ACTION"
VERIFY = "VERIFY"
STORE_MEMORY = "STORE_MEMORY"
END = "END"

# Map a tool name to (start_event, ok_event, fail_event) for rich telemetry.
_TOOL_EVENTS = {
    "run_tests": (EventType.TEST_STARTED, EventType.TEST_PASSED, EventType.TEST_FAILED),
    "deploy": (EventType.DEPLOY_STARTED, EventType.DEPLOY_COMPLETED, EventType.TOOL_FAILED),
}

# ── event-enrichment helpers ────────────────────────────────────
# These only *read* real execution state and shape it onto the event ``data``
# payload the existing frontend panels already consume. Nothing here fabricates
# values: every field comes from a ToolResult / RecoveryDecision / plan / model
# that genuinely exists during a live run.

# Coarse UI pipeline-stage hint (matches the frontend stage-ribbon ids). Purely
# a display aid so the ribbon advances in LIVE mode; it never drives execution.
_UI_STAGE = {
    "list_dir": "INSPECT",
    "read_file": "INSPECT",
    "run_command": "INSPECT",
    "write_file": "CODE",
    "run_tests": "TEST",
    "http_check": "VERIFY",
    "deploy": "DEPLOY",
}


def _ui_stage(tool: Optional[str]) -> str:
    return _UI_STAGE.get(tool or "", "INSPECT")


def _safe_args(args: Optional[dict], limit: int = 300) -> dict:
    """Truncate long/opaque arg values for transport. The builtin toolbelt takes
    paths/commands/content — never secrets — but we still cap large blobs (e.g.
    file ``content``) so events stay small and never dump whole files."""
    out: dict = {}
    for k, v in (args or {}).items():
        if isinstance(v, str) and len(v) > limit:
            out[k] = v[:limit] + "…"
        else:
            out[k] = v
    return out


def _tool_start_fields(tool: Optional[str], args: Optional[dict]) -> dict:
    """Descriptive fields for a TOOL_STARTED/TEST_STARTED/DEPLOY_STARTED event,
    derived from the task's real ``tool_args``."""
    args = args or {}
    fields: dict = {"action": tool, "args": _safe_args(args)}
    if tool in ("run_command", "run_tests") and args.get("command"):
        fields["command"] = args["command"]
    if tool == "run_tests":
        fields["suite"] = args.get("command", "pytest -q")
    if tool in ("read_file", "write_file", "list_dir") and args.get("path"):
        fields["path"] = args["path"]
        fields["target"] = args["path"]
    if tool == "http_check" and args.get("url"):
        fields["url"] = args["url"]
    if tool == "deploy":
        fields["environment"] = args.get("environment", "preview")
    return fields


# pytest summary line, e.g. "195 passed, 1 skipped in 3.4s" / "2 failed, 14 passed"
_PYTEST_COUNT = re.compile(r"(\d+)\s+(passed|failed|skipped|error|errors|xfailed|xpassed)")


def _parse_pytest(output: str) -> dict:
    """Extract real pass/fail/skip counts and failing-test lines from pytest
    output. Returns only what is actually present — no invented numbers."""
    text = output or ""
    counts: dict[str, int] = {}
    for m in _PYTEST_COUNT.finditer(text):
        n, kind = int(m.group(1)), m.group(2)
        kind = "errors" if kind == "error" else kind
        counts[kind] = counts.get(kind, 0) + n
    passed = counts.get("passed")
    failed = counts.get("failed", 0) + counts.get("errors", 0) or counts.get("failed")
    skipped = counts.get("skipped")
    fields: dict = {}
    if passed is not None:
        fields["passed"] = passed
    if counts.get("failed") is not None or counts.get("errors"):
        fields["failed"] = counts.get("failed", 0) + counts.get("errors", 0)
    if skipped is not None:
        fields["skipped"] = skipped
    total = None
    if passed is not None or fields.get("failed") is not None:
        total = (passed or 0) + fields.get("failed", 0) + (skipped or 0)
    if total:
        fields["total"] = total
    # Failing test identifiers (pytest prints "FAILED path::test - reason").
    failures = [ln.strip() for ln in text.splitlines()
                if ln.strip().startswith(("FAILED ", "ERROR "))][:10]
    if failures:
        fields["failures"] = failures
    return fields


def _memory_summary(mr) -> dict:
    """Non-sensitive projection of a retrieved MemoryResult for the memory
    panel. Surfaces id/scope/tags + a truncated content summary only — never
    embeddings, user ids, or raw stored blobs."""
    rec = mr.record
    content = (rec.content or "").strip()
    first_line = content.splitlines()[0] if content else ""
    return {
        "id": rec.id,
        "similarity": round(float(mr.score), 4),
        "scope": rec.scope.value,
        "tags": list(rec.tags or []),
        "title": (first_line[:120] + "…") if len(first_line) > 120 else first_line,
        "previous_resolution": (content[:400] + "…") if len(content) > 400 else content,
    }


def _run_stats(history: list) -> dict:
    """Aggregate honest execution statistics from the observed event history."""
    tool_calls = sum(1 for e in history if e.type in (
        EventType.TOOL_COMPLETED, EventType.TEST_PASSED, EventType.DEPLOY_COMPLETED))
    recoveries = sum(1 for e in history if e.type == EventType.RECOVERY_STARTED)
    files = {e.data.get("file") for e in history
             if e.type == EventType.CODE_CHANGED and e.data.get("file")}
    return {
        "tool_calls": tool_calls,
        "recoveries": recoveries,
        "files_changed": len(files),
    }


class Orchestrator:
    def __init__(
        self,
        provider: Optional[ModelProvider] = None,
        memory: Optional[MemoryManager] = None,
        registry: Optional[ToolRegistry] = None,
        settings: Optional[Settings] = None,
        event_bus: Optional[EventBus] = None,
        permissions: Optional[PermissionManager] = None,
    ):
        self.settings = settings or get_settings()
        self.provider = provider or get_provider(settings=self.settings)
        self.memory = memory or MemoryManager(settings=self.settings)
        self.registry = registry or register_builtins(ToolRegistry())
        self.events = event_bus or EventBus()
        self.permissions = permissions or PermissionManager(autonomy=self.settings.autonomy)
        self.planner = Planner(self.provider, self.memory)
        self.recovery = RecoveryEngine(
            max_task_retries=self.settings.max_task_retries,
            max_plan_revisions=self.settings.max_plan_revisions,
        )
        self.verifier = Verifier(self.registry)
        self._max_steps = 200

    # ── public API ──────────────────────────────────────────────
    def run(
        self,
        objective: str,
        project: Optional[str] = None,
        approvals: Optional[list[str]] = None,
    ) -> tuple[AgentState, ExecutionResult]:
        state = AgentState(objective=objective, project=project)
        return self.resume(state, approvals=approvals)

    def resume(
        self, state: AgentState, approvals: Optional[list[str]] = None
    ) -> tuple[AgentState, ExecutionResult]:
        for tool in approvals or []:
            self.permissions.approve(tool=tool)
        if state.node in (START, "", None):
            state.node = UNDERSTAND
        if state.status == ExecutionStatus.AWAITING_APPROVAL:
            state.status = ExecutionStatus.RUNNING

        steps = 0
        while state.node != END and steps < self._max_steps:
            steps += 1
            handler = self._dispatch.get(state.node)
            if handler is None:
                state.error = f"unknown node {state.node!r}"
                state.status = ExecutionStatus.FAILED
                break
            try:
                next_node = handler(self, state)
            except Exception as exc:
                # A handler raised — most likely a real model/provider call in
                # CREATE_PLAN. Convert it into KALKI's existing terminal failure
                # state (FAILED + OBJECTIVE_FAILED) instead of letting it escape
                # the loop and leave the run hanging. Fallback selection is
                # untouched; this is a genuine call-time failure, not a retry.
                next_node = self._fail_from_exception(state, exc)
            state.node = next_node
            state.touch()
            # Pause the drive loop when we need a human.
            if state.status == ExecutionStatus.AWAITING_APPROVAL:
                break

        if steps >= self._max_steps and state.status == ExecutionStatus.RUNNING:
            state.status = ExecutionStatus.FAILED
            state.error = "exceeded maximum steps"

        return state, self._result(state)

    # ── node handlers ───────────────────────────────────────────
    def _understand(self, state: AgentState) -> str:
        self.events.publish(EventType.LOG, state.id,
                            f"Understanding objective: {state.objective}")
        self.memory.record_session(state.id, f"OBJECTIVE: {state.objective}",
                                   tags=["objective"], project=state.project, user_id=state.user_id)
        return CREATE_PLAN

    def _create_plan(self, state: AgentState) -> str:
        plan, recalled = self.planner.create_plan(state.objective, state.project, state.user_id)
        state.plan = plan
        state.retrieved_memories = recalled
        if recalled:
            self.events.publish(
                EventType.MEMORY_RETRIEVED, state.id,
                f"Recalled {len(recalled)} relevant memories",
                memories=[m.to_dict() for m in recalled],
            )
        self.events.publish(EventType.PLAN_CREATED, state.id,
                            f"Plan with {len(plan.tasks)} tasks",
                            plan=plan.to_dict())
        self.memory.record_session(
            state.id, f"PLAN: {[t.description for t in plan.tasks]}",
            tags=["plan"], project=state.project, user_id=state.user_id,
        )
        return SELECT_NEXT

    def _select_next(self, state: AgentState) -> str:
        assert state.plan is not None
        if state.plan.is_complete():
            return VERIFY
        task = state.plan.next_task()
        if task is None:
            # No runnable task but not complete -> blocked/failed.
            if state.plan.has_failure():
                state.status = ExecutionStatus.FAILED
                state.error = "plan has an unrecoverable failed task"
            else:
                state.status = ExecutionStatus.BLOCKED
                state.error = "no runnable task (dependency deadlock)"
            return STORE_MEMORY
        state.current_task_id = task.id
        task.status = TaskStatus.RUNNING
        self.events.publish(EventType.TASK_STARTED, state.id,
                            task.description, task_id=task.id)
        return EXECUTE

    def _execute(self, state: AgentState) -> str:
        assert state.plan is not None
        task = state.plan.get(state.current_task_id or "")
        if task is None:
            state.status = ExecutionStatus.FAILED
            state.error = "current task missing"
            return STORE_MEMORY

        tool_name = task.tool
        if not tool_name or not self.registry.has(tool_name):
            # No executable tool: treat as a reasoning/no-op step, complete it.
            self.events.publish(EventType.LOG, state.id,
                                f"No tool for task {task.id}; marking as reasoning step")
            task.status = TaskStatus.COMPLETED
            self.events.publish(EventType.TASK_COMPLETED, state.id,
                                task.description, task_id=task.id)
            return SELECT_NEXT

        # Permission gate.
        risk: RiskLevel = self.registry.risk_of(tool_name)
        decision = self.permissions.check(tool_name, risk)
        if not decision.allowed:
            self.events.publish(
                EventType.APPROVAL_REQUIRED, state.id, decision.reason,
                task_id=task.id, tool=tool_name, risk=risk.value,
            )
            state.status = ExecutionStatus.AWAITING_APPROVAL
            state.scratch["pending_tool"] = tool_name
            return EXECUTE  # re-enter here on resume once approved

        # Execute.
        ctx = ToolContext(workspace_root=self.settings.workspace_root,
                          run_id=state.id, project=state.project,
                          scratch=state.scratch)
        start_evt, ok_evt, fail_evt = _TOOL_EVENTS.get(
            tool_name, (EventType.TOOL_STARTED, EventType.TOOL_COMPLETED, EventType.TOOL_FAILED)
        )
        self.events.publish(start_evt, state.id, f"{tool_name} {task.tool_args}",
                            task_id=task.id, tool=tool_name)
        task.attempts += 1
        tool = self.registry.get(tool_name)
        result = tool.invoke(task.tool_args, ctx)  # type: ignore[union-attr]
        task.result = result

        if result.ok:
            self.events.publish(ok_evt, state.id, "ok", task_id=task.id,
                                tool=tool_name, output=_trim(result.output))
            if result.metadata.get("code_changed"):
                self.events.publish(EventType.CODE_CHANGED, state.id,
                                    "working tree modified", task_id=task.id)
        else:
            self.events.publish(fail_evt, state.id, result.error or "failed",
                                task_id=task.id, tool=tool_name,
                                failure_class=str(result.failure_class))
        return OBSERVE

    def _observe(self, state: AgentState) -> str:
        assert state.plan is not None
        task = state.plan.get(state.current_task_id or "")
        assert task is not None and task.result is not None
        if task.result.ok:
            task.status = TaskStatus.COMPLETED
            self.memory.record_session(
                state.id, f"TASK OK [{task.id}] {task.description}",
                tags=["task", "success"], project=state.project, user_id=state.user_id,
            )
            self.events.publish(EventType.TASK_COMPLETED, state.id,
                                task.description, task_id=task.id)
            return SELECT_NEXT
        task.error = task.result.error
        self.memory.record_session(
            state.id, f"TASK FAIL [{task.id}] {task.description}: {task.error}",
            tags=["task", "failure"], project=state.project, user_id=state.user_id,
        )
        return DECIDE

    def _decide(self, state: AgentState) -> str:
        assert state.plan is not None
        task = state.plan.get(state.current_task_id or "")
        assert task is not None and task.result is not None
        decision = self.recovery.decide(task, task.result, state.plan_revisions)
        self.events.publish(EventType.RECOVERY_STARTED, state.id,
                            f"{decision.action}: {decision.reason}",
                            task_id=task.id, action=decision.action)

        if decision.action == RETRY:
            task.status = TaskStatus.PENDING  # eligible to be re-selected
            return SELECT_NEXT

        if decision.action == REPLAN:
            self.planner.revise_after_failure(state.plan, task, decision.diagnosis)
            state.plan_revisions += 1
            self.events.publish(EventType.PLAN_REVISED, state.id,
                                f"revision {state.plan.revision}",
                                plan=state.plan.to_dict())
            return SELECT_NEXT

        if decision.action == ESCALATE:
            self.events.publish(EventType.APPROVAL_REQUIRED, state.id,
                                decision.reason, task_id=task.id)
            state.status = ExecutionStatus.AWAITING_APPROVAL
            return EXECUTE

        # ABORT
        task.status = TaskStatus.FAILED
        state.status = ExecutionStatus.FAILED
        state.error = decision.diagnosis
        self.events.publish(EventType.TASK_FAILED, state.id, decision.diagnosis,
                            task_id=task.id)
        return STORE_MEMORY

    def _verify(self, state: AgentState) -> str:
        self.events.publish(EventType.VERIFICATION_STARTED, state.id,
                            "verifying end state")
        ctx = ToolContext(workspace_root=self.settings.workspace_root,
                          run_id=state.id, project=state.project,
                          scratch=state.scratch)
        report = self.verifier.verify(state, ctx)
        state.scratch["verification"] = {
            "verified": report.verified, "checks": report.checks,
            "summary": report.summary,
        }
        self.events.publish(EventType.VERIFICATION_COMPLETED, state.id,
                            report.summary, verified=report.verified,
                            checks=report.checks)
        state.status = (ExecutionStatus.COMPLETED if report.verified
                        else ExecutionStatus.FAILED)
        if not report.verified and not state.error:
            state.error = f"verification failed: {report.summary}"
        return STORE_MEMORY

    def _store_memory(self, state: AgentState) -> str:
        outcome = state.status.value
        verified = bool(state.scratch.get("verification", {}).get("verified"))
        lesson = self._compose_lesson(state, outcome, verified)
        self.memory.record_experience(
            lesson, project=state.project, user_id=state.user_id,
            tags=["incident", outcome], objective=state.objective,
            verified=verified,
        )
        self.events.publish(EventType.MEMORY_STORED, state.id,
                            "engineering experience persisted")
        if state.status == ExecutionStatus.COMPLETED:
            self.events.publish(EventType.OBJECTIVE_COMPLETED, state.id,
                                "objective complete and verified")
        elif state.status == ExecutionStatus.FAILED:
            self.events.publish(EventType.OBJECTIVE_FAILED, state.id,
                                state.error or "objective failed")
        return END

    # ── helpers ─────────────────────────────────────────────────
    @staticmethod
    def _compose_lesson(state: AgentState, outcome: str, verified: bool) -> str:
        steps = []
        if state.plan:
            for t in state.plan.tasks:
                mark = {TaskStatus.COMPLETED: "ok", TaskStatus.FAILED: "FAIL"}.get(
                    t.status, t.status.value)
                steps.append(f"[{mark}] {t.description}")
        return (
            f"OBJECTIVE: {state.objective}\n"
            f"OUTCOME: {outcome} (verified={verified})\n"
            f"STEPS:\n" + "\n".join(steps)
        )

    def _fail_from_exception(self, state: AgentState, exc: Exception) -> str:
        """Turn an unhandled handler/provider exception into KALKI's existing
        FAILED terminal state and an ``OBJECTIVE_FAILED`` event, preserving the
        error detail. Returns ``END``. Never re-raises: a best-effort attempt to
        persist the failure experience is guarded so a second failure (e.g. the
        memory backend being down) cannot escape."""
        detail = f"{state.node}: {type(exc).__name__}: {exc}"
        state.status = ExecutionStatus.FAILED
        state.error = detail[:500]
        self.events.publish(EventType.OBJECTIVE_FAILED, state.id, state.error,
                            node=state.node, error_type=type(exc).__name__)
        try:
            self.memory.record_experience(
                self._compose_lesson(state, "failed", False),
                project=state.project, user_id=state.user_id,
                tags=["incident", "failed", "exception"], objective=state.objective,
            )
            self.events.publish(EventType.MEMORY_STORED, state.id,
                                "failure experience persisted")
        except Exception:
            pass
        return END

    def _result(self, state: AgentState) -> ExecutionResult:
        verified = bool(state.scratch.get("verification", {}).get("verified"))
        summary = state.scratch.get("verification", {}).get("summary", "") \
            if state.status == ExecutionStatus.COMPLETED else (state.error or "")
        return ExecutionResult(
            run_id=state.id, objective=state.objective, status=state.status,
            plan=state.plan, verified=verified, error=state.error,
            event_count=len(self.events.history()), summary=summary,
            metadata={"node": state.node, "plan_revisions": state.plan_revisions},
        )

    _dispatch = {
        UNDERSTAND: _understand,
        CREATE_PLAN: _create_plan,
        SELECT_NEXT: _select_next,
        EXECUTE: _execute,
        OBSERVE: _observe,
        DECIDE: _decide,
        VERIFY: _verify,
        STORE_MEMORY: _store_memory,
    }


def _trim(value, limit: int = 400):
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[:limit] + "…"
