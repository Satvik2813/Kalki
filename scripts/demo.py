"""End-to-end KALKI demo — runs fully offline (mock model + local memory).

Shows the closed loop on a single objective, including a tool failure that the
agent recovers from, verification, and persisted experience. Run:

    python scripts/demo.py
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.orchestrator import Orchestrator  # noqa: E402
from agent.tools.base import Tool, ToolContext, ToolRegistry  # noqa: E402
from agent.tools.builtins import register_builtins  # noqa: E402
from config.settings import Settings  # noqa: E402
from memory.manager import MemoryManager  # noqa: E402
from models.mock import MockProvider  # noqa: E402
from shared.contracts import (  # noqa: E402
    FailureClass,
    Plan,
    RiskLevel,
    Task,
    ToolResult,
    ToolSpec,
)


class FlakyDeploy(Tool):
    """Deploy that fails transiently once, then succeeds — to exercise the
    capture -> classify -> retry -> success recovery path."""

    spec = ToolSpec(name="flaky_deploy", description="Flaky deploy",
                    risk=RiskLevel.SAFE)

    def run(self, args, ctx: ToolContext) -> ToolResult:
        n = ctx.scratch.get("_deploy_attempts", 0) + 1
        ctx.scratch["_deploy_attempts"] = n
        if n < 2:
            return ToolResult.failure(self.spec.name,
                                      "registry timeout (transient)",
                                      FailureClass.TRANSIENT)
        url = f"https://preview.kalki.local/{ctx.run_id}"
        return ToolResult.success(self.spec.name, output={"url": url},
                                  deploy_url=url)


class ScriptedProvider(MockProvider):
    def plan(self, objective, context=""):
        return Plan(objective=objective, tasks=[
            Task(id="task-1", description="Inspect the repository",
                 tool="list_dir", tool_args={"path": "."}),
            Task(id="task-2", description="Write the fix",
                 tool="write_file", depends_on=["task-1"],
                 tool_args={"path": "fix.txt", "content": "corrected logic"}),
            Task(id="task-3", description="Run the test suite",
                 tool="run_tests", depends_on=["task-2"],
                 tool_args={"command": "python -c \"print('3 passed')\""}),
            Task(id="task-4", description="Deploy to preview",
                 tool="flaky_deploy", depends_on=["task-3"]),
        ])


def main() -> int:
    workspace = tempfile.mkdtemp(prefix="kalki_demo_")
    db = os.path.join(workspace, "memory.sqlite3")
    settings = Settings(model_provider="mock", memory_backend="local",
                        local_db_path=db, autonomy="autonomous",
                        workspace_root=workspace)
    registry = register_builtins(ToolRegistry())
    registry.register(FlakyDeploy())
    memory = MemoryManager(settings=settings)

    orch = Orchestrator(provider=ScriptedProvider(), memory=memory,
                        registry=registry, settings=settings)

    objective = ("Fix the authentication bug in this project, test the fix, "
                 "deploy it, and verify the deployment.")
    print(f"\n=== KALKI objective ===\n{objective}\n")
    print("=== execution event stream ===")

    def on_event(e):
        print(f"  [{e.seq:>2}] {e.type.value:<22} {e.message[:70]}")

    orch.events.subscribe(on_event)
    state, result = orch.run(objective, project="demo-project")

    print("\n=== result ===")
    print(f"  status   : {result.status.value}")
    print(f"  verified : {result.verified}")
    print(f"  revisions: {result.metadata['plan_revisions']}")
    print(f"  events   : {result.event_count}")
    print("\n=== final plan ===")
    for t in state.plan.tasks:
        print(f"  [{t.status.value:<9}] {t.description}  (attempts={t.attempts})")

    print("\n=== persisted long-term experience ===")
    from shared.contracts import MemoryScope
    for r in memory.store.list(scope=MemoryScope.LONG_TERM):
        print("  " + r.content.replace("\n", "\n  "))

    memory.close()
    return 0 if result.status.value == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
