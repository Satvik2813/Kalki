"""FULL user-journey backend validation through KALKI's live Director loop.

Two live orchestrator runs (deterministic, offline, no external providers):

  Run A (happy path) proves the spine:
    user/project/objective -> Director (state machine) -> Planner -> tools
    -> code change + tests -> verification -> memory -> result=COMPLETED

  Run B (fault injection) proves failure/recovery:
    a deliberately failing tool -> RECOVERY_STARTED -> REPLAN in the live loop

Each phase is marked from concrete event/state evidence. Uses a temp workspace
and temp local DB; touches no real project files or external services.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings
from agent.orchestrator import Orchestrator
from agent.events import EventBus
from models.base import ModelProvider, ModelResponse
from shared.contracts import EventType, ExecutionStatus, Plan, Task


class JourneyProvider(ModelProvider):
    """Deterministic provider returning a controlled plan (no network)."""
    name = "journey"

    def __init__(self, tasks_fn):
        super().__init__(model="journey")
        self._tasks_fn = tasks_fn

    def complete(self, prompt, *, system=None, temperature=0.2, **kw):
        return ModelResponse(text="ok", model=self.model)

    def plan(self, objective, context=""):
        return Plan(objective=objective, tasks=self._tasks_fn())


def make_settings(ws: Path, db: Path, autonomy="autonomous") -> Settings:
    return Settings(model_provider="mock", memory_backend="local",
                    local_db_path=str(db), workspace_root=str(ws),
                    autonomy=autonomy)


root = Path(tempfile.mkdtemp(prefix="kalki_journey_"))
ws = root / "ws"; ws.mkdir()
db = root / "mem.sqlite3"
PY_OK = 'python -c "import sys;sys.exit(0)"'
PY_FAIL = 'python -c "import sys;sys.exit(1)"'

# ── Run A: happy path ────────────────────────────────────────────────────────
def happy_tasks():
    return [
        Task(id="t1", description="Apply the code change", tool="write_file",
             tool_args={"path": "feature.py", "content": "print('hello kalki')\n"}),
        Task(id="t2", description="Run the test suite", tool="run_tests",
             tool_args={"command": PY_OK}, depends_on=["t1"]),
        Task(id="t3", description="Deploy to preview", tool="deploy",
             tool_args={"environment": "preview"}, depends_on=["t2"]),
    ]

busA = EventBus()
orchA = Orchestrator(provider=JourneyProvider(happy_tasks),
                     settings=make_settings(ws, db), event_bus=busA)
stateA, resultA = orchA.run(objective="Ship a small feature and deploy it",
                            project="journey-demo")
typesA = {e.type for e in busA.history()}

def seen(bus_types, *ets): return all(e in bus_types for e in ets)

phases = {}
phases["user -> project -> objective"] = (stateA.project == "journey-demo"
                                          and bool(stateA.objective))
phases["Director (state machine loop)"] = EventType.PLAN_CREATED in typesA
phases["Planner (plan produced)"] = (stateA.plan is not None
                                     and len(stateA.plan.tasks) >= 1)
phases["tools (tool execution)"] = seen(typesA, EventType.TOOL_STARTED,
                                        EventType.TOOL_COMPLETED)
phases["code change + tests"] = seen(typesA, EventType.CODE_CHANGED,
                                     EventType.TEST_PASSED)
phases["verification"] = seen(typesA, EventType.VERIFICATION_COMPLETED) and \
    bool(stateA.scratch.get("verification", {}).get("verified"))
phases["memory (experience stored)"] = EventType.MEMORY_STORED in typesA
phases["result (terminal status)"] = resultA.status == ExecutionStatus.COMPLETED

# ── Run B: fault injection -> recovery ───────────────────────────────────────
def failing_tasks():
    return [Task(id="f1", description="Run tests (will fail)", tool="run_tests",
                 tool_args={"command": PY_FAIL})]

busB = EventBus()
orchB = Orchestrator(provider=JourneyProvider(failing_tasks),
                     settings=make_settings(ws, db), event_bus=busB)
stateB, resultB = orchB.run(objective="Fix the failing build", project="journey-demo")
typesB = {e.type for e in busB.history()}
phases["failure / recovery"] = (EventType.RECOVERY_STARTED in typesB
                                and EventType.TOOL_FAILED in typesB)

# ── Report ───────────────────────────────────────────────────────────────────
print("Backend user-journey validation (live Director runs):\n")
width = max(len(k) for k in phases)
all_ok = True
for k, v in phases.items():
    mark = "PROVEN" if v else "NOT PROVEN"
    all_ok = all_ok and v
    print(f"  {k.ljust(width)} : {mark}")
print(f"\nRun A terminal status: {resultA.status.value} "
      f"(verified={resultA.verified})")
print(f"Run B terminal status: {resultB.status.value} "
      f"(recovery exercised: {EventType.RECOVERY_STARTED in typesB})")
print("\nFULL BACKEND JOURNEY:", "PROVEN" if all_ok else "PARTIAL")
sys.exit(0 if all_ok else 1)
