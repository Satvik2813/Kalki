# KALKI Contracts

These are the **stable integration surfaces**. Dev 2 (frontend/API) and Dev 3
(tools) build against them and never modify the core. All types live in
`shared/contracts.py`, are stdlib-only, and provide `to_dict()`/`from_dict()`.

Compatibility rule: fields may be **added** (optional); existing field meanings
do not change without a version bump.

## Core types

### Task
```python
Task(
  id: str, description: str,
  status: TaskStatus = "pending",              # pending|running|completed|failed|skipped|blocked
  tool: str | None = None, tool_args: dict = {},
  depends_on: list[str] = [], attempts: int = 0,
  result: ToolResult | None = None, error: str | None = None,
  metadata: dict = {},
)
```

### Plan
```python
Plan(objective: str, tasks: list[Task], revision: int = 0, metadata: dict = {})
plan.next_task()   # first pending task whose deps are all completed
plan.is_complete() # all tasks completed/skipped
```

### ToolResult  (the uniform tool return)
```python
ToolResult.success(tool, output=..., **metadata)
ToolResult.failure(tool, error, failure_class=FailureClass.TRANSIENT, **metadata)
# fields: ok, tool, output, error, failure_class, duration_ms, metadata
```
`FailureClass ∈ {transient, tool_error, logic_error, permission, fatal, unknown}`
drives recovery — classify failures correctly.

### MemoryRecord / MemoryResult
```python
MemoryRecord(scope: MemoryScope, content: str, project=None, session_id=None,
             tags=[], metadata={}, embedding=None, created_at=...)
MemoryResult(record: MemoryRecord, score: float)   # score ∈ [0,1]
# MemoryScope ∈ {session, project, long_term}
```

### AgentEvent
```python
AgentEvent(type: EventType, task_id: str, message: str, data: dict, seq: int, timestamp: str)
```
`task_id` is the run id. `seq` is monotonic per run — poll with `?after=seq`.
See `docs/AGENT_FLOW.md` for the full `EventType` list.

### AgentState / ExecutionResult
`AgentState` is the full serialisable execution state (objective, plan, node,
status, events, retrieved_memories, scratch). `ExecutionResult` is the terminal
report (`status`, `verified`, `summary`, `error`).
`ExecutionStatus ∈ {completed, failed, blocked, awaiting_approval, running}`.

```python
class AgentState(BaseModel):
    id: str                   # Unique run identifier
    user_id: Optional[str]    # ID of the user owning this run
    objective: str            # Original goal
    project: Optional[str]    # Project scoping (for memory separation)
    status: ExecutionStatus   # RUNNING | COMPLETED | FAILED | BLOCKED | AWAITING_APPROVAL
    node: str                 # Current node in orchestrator state machine
    plan: Optional[Plan]      # Current execution plan
    current_task_id: Optional[str]
    plan_revisions: int       # Tracks how many times we've had to replan
    error: Optional[str]      # Top-level failure reason if FAILED
    retrieved_memories: list[MemoryResult]
```

## Authoring a Tool (Dev 3)

```python
from agent.tools.base import Tool, ToolContext
from shared.contracts import ToolSpec, ToolResult, RiskLevel, FailureClass

class GitHubIssueTool(Tool):
    spec = ToolSpec(
        name="github_open_issue",
        description="Open a GitHub issue.",
        parameters={"title": "str", "body": "str"},
        risk=RiskLevel.ELEVATED,          # gated unless approved / autonomous
    )
    def run(self, args, ctx: ToolContext) -> ToolResult:
        try:
            number = ...  # call the API using args, ctx.project
            return ToolResult.success(self.spec.name, output={"number": number})
        except TimeoutError as e:
            return ToolResult.failure(self.spec.name, str(e), FailureClass.TRANSIENT)

# register:  registry.register(GitHubIssueTool())
```
Rules: never raise for expected failures (return a classified `ToolResult`);
respect `ctx.workspace_root`; pick the right `RiskLevel`.

## API contract (Dev 2)

Base: `/api`. Bodies/returns are JSON (`to_dict()` shapes above).

| Method & path | Purpose | Body / query | Returns |
|---|---|---|---|
| `POST /api/tasks` | create a run | `{objective, project?, autonomy?, start?}` | `AgentState` |
| `GET /api/tasks` | list runs | — | `{tasks: AgentState[]}` |
| `GET /api/tasks/{id}` | run state | — | `AgentState` |
| `POST /api/tasks/{id}/start` | begin execution | — | `{run_id, status, started}` |
| `POST /api/tasks/{id}/approve` | approve gated tools + resume | `{tools: string[]}` | `{run_id, approved, status}` |
| `GET /api/tasks/{id}/events` | events | `?after=seq` (JSON) or `?stream=1` (SSE) | `{events: AgentEvent[]}` / event stream |
| `GET /api/tasks/{id}/result` | terminal result | — | `ExecutionResult` |
| `GET /api/projects` | known projects | — | `{projects: string[]}` |
| `GET /api/memory` | recent memories | `?limit` | `{memories: MemoryRecord[]}` |
| `GET /health` | liveness | — | `{status, runs}` |

**Realtime:** SSE frames are `event: <EventType>\ndata: <AgentEvent json>`; the
stream replays history first (so late subscribers miss nothing) and closes with
an `_end` event when the run reaches a terminal/awaiting state. For non-SSE
clients, poll `GET …/events?after=<last seq>`.

**Approval flow:** if a run's status is `awaiting_approval`, inspect the last
`APPROVAL_REQUIRED` event's `data.tool`, then `POST …/approve {"tools":[tool]}`.
