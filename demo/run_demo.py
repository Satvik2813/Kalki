"""Deterministic KALKI demo — end-to-end autonomous engineering loop.

Demonstrates KALKI fixing a real auth bug, running tests, deploying,
and verifying — with deterministic failure recovery.

Run:
    python demo/run_demo.py
"""
from __future__ import annotations

import os
import shutil
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
from tools.filesystem import register_filesystem_tools  # noqa: E402
from tools.terminal import register_terminal_tools  # noqa: E402
from tools.git_tool import register_git_tools  # noqa: E402


class FlakyDeploy(Tool):
    """Deploy that fails transiently once, then succeeds — exercises
    the recovery path."""

    spec = ToolSpec(name="flaky_deploy", description="Flaky deploy",
                    risk=RiskLevel.SAFE)

    def run(self, args, ctx: ToolContext) -> ToolResult:
        n = ctx.scratch.get("_demo_deploy_attempts", 0) + 1
        ctx.scratch["_demo_deploy_attempts"] = n
        if n < 2:
            return ToolResult.failure(self.spec.name,
                                      "registry timeout (transient)",
                                      FailureClass.TRANSIENT)
        url = f"https://preview.kalki.local/{ctx.run_id}"
        return ToolResult.success(self.spec.name, output={"url": url},
                                  deploy_url=url)


class DemoProvider(MockProvider):
    """Scripted model provider for deterministic demo flow."""

    def plan(self, objective, context=""):
        return Plan(objective=objective, tasks=[
            Task(id="task-1", description="Inspect the project files",
                 tool="fs_list",
                 tool_args={"path": ".", "recursive": True, "pattern": "*.py"}),
            Task(id="task-2", description="Read the auth module to find the bug",
                 tool="fs_read", depends_on=["task-1"],
                 tool_args={"path": "auth.py"}),
            Task(id="task-3", description="Fix the auth bug (AUTH_SECRET_KEY → SECRET_KEY)",
                 tool="fs_edit", depends_on=["task-2"],
                 tool_args={
                     "path": "auth.py",
                     "old_text": "config.AUTH_SECRET_KEY",
                     "new_text": "config.SECRET_KEY",
                 }),
            Task(id="task-4", description="Run the test suite to verify the fix",
                 tool="run_tests", depends_on=["task-3"],
                 tool_args={"command": "py -m pytest test_app.py -v"}),
            Task(id="task-5", description="Deploy the fix to preview",
                 tool="flaky_deploy", depends_on=["task-4"]),
        ])


def _setup_demo_workspace() -> str:
    """Copy the demo project to a temporary workspace."""
    workspace = tempfile.mkdtemp(prefix="kalki_demo_")
    demo_src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "project")

    # Copy demo project files to workspace root.
    for name in ("config.py", "auth.py", "app.py", "test_app.py", "__init__.py"):
        src = os.path.join(demo_src, name)
        if os.path.exists(src):
            shutil.copy2(src, workspace)

    return workspace


def main() -> int:
    workspace = _setup_demo_workspace()
    db = os.path.join(workspace, "memory.sqlite3")
    settings = Settings(
        model_provider="mock", memory_backend="local",
        local_db_path=db, autonomy="autonomous",
        workspace_root=workspace,
    )

    # Build the registry with Dev 3 tools.
    registry = register_builtins(ToolRegistry())
    register_filesystem_tools(registry)
    register_terminal_tools(registry)
    register_git_tools(registry)
    registry.register(FlakyDeploy())

    memory = MemoryManager(settings=settings)
    orch = Orchestrator(
        provider=DemoProvider(), memory=memory,
        registry=registry, settings=settings,
    )

    objective = (
        "Fix the authentication bug in this project, run the tests to "
        "verify the fix, deploy it, and verify the deployment."
    )

    print(f"\n{'='*60}")
    print("  KALKI — Autonomous AI Software Engineer Demo")
    print(f"{'='*60}")
    print(f"\n  Objective: {objective}\n")
    print(f"  Workspace: {workspace}\n")
    print(f"{'='*60}")
    print("  Execution Event Stream")
    print(f"{'='*60}")

    def on_event(e):
        print(f"  [{e.seq:>2}] {e.type.value:<22} {e.message[:70]}")

    orch.events.subscribe(on_event)
    state, result = orch.run(objective, project="demo-project")

    print(f"\n{'='*60}")
    print("  Result")
    print(f"{'='*60}")
    print(f"  Status    : {result.status.value}")
    print(f"  Verified  : {result.verified}")
    print(f"  Revisions : {result.metadata['plan_revisions']}")
    print(f"  Events    : {result.event_count}")

    print(f"\n{'='*60}")
    print("  Final Plan")
    print(f"{'='*60}")
    if state.plan:
        for t in state.plan.tasks:
            print(f"  [{t.status.value:<9}] {t.description}  (attempts={t.attempts})")

    memory.close()

    if result.status.value == "completed" and result.verified:
        print(f"\n  ✓ DEMO SUCCESSFUL — KALKI autonomously fixed, tested, and deployed.")
        return 0
    else:
        print(f"\n  ✗ DEMO INCOMPLETE — status={result.status.value}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
