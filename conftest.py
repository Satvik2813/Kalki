"""Pytest configuration — ensures the repo root is importable and provides
shared fixtures (isolated settings, service, controlled tools)."""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent.tools.base import Tool, ToolContext, ToolRegistry  # noqa: E402
from agent.tools.builtins import register_builtins  # noqa: E402
from config.settings import Settings  # noqa: E402
from memory.manager import MemoryManager  # noqa: E402
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "kalki_test.sqlite3")


@pytest.fixture()
def settings(tmp_path, tmp_db):
    return Settings(
        model_provider="mock",
        memory_backend="local",
        local_db_path=tmp_db,
        autonomy="autonomous",
        workspace_root=str(tmp_path),
        max_task_retries=2,
        max_plan_revisions=3,
    )


@pytest.fixture()
def memory(settings):
    mm = MemoryManager(settings=settings)
    yield mm
    mm.close()


class FlakyTool(Tool):
    """Fails transiently on the first attempt, succeeds afterwards. Used to
    demonstrate capture -> classify -> retry -> success."""

    spec = ToolSpec(name="flaky_build", description="Flaky build step",
                    risk=RiskLevel.SAFE)

    def run(self, args, ctx: ToolContext) -> ToolResult:
        count = ctx.scratch.get("_flaky_attempts", 0) + 1
        ctx.scratch["_flaky_attempts"] = count
        if count < 2:
            return ToolResult.failure(self.spec.name, "network blip",
                                      FailureClass.TRANSIENT)
        return ToolResult.success(self.spec.name, output="built ok")


class AlwaysFailTool(Tool):
    """Always fails with a logic error — drives replanning to exhaustion."""

    spec = ToolSpec(name="always_fail", description="Always fails",
                    risk=RiskLevel.SAFE)

    def run(self, args, ctx: ToolContext) -> ToolResult:
        return ToolResult.failure(self.spec.name, "cannot converge",
                                  FailureClass.LOGIC_ERROR)


@pytest.fixture()
def registry():
    reg = register_builtins(ToolRegistry())
    reg.register(FlakyTool())
    reg.register(AlwaysFailTool())
    return reg
