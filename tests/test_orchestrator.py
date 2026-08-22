"""Orchestrator: state transitions, recovery, verification, approvals, and the
required end-to-end integration test."""
from agent.orchestrator import END, Orchestrator
from agent.permissions import PermissionManager
from models.mock import MockProvider
from shared.contracts import (
    EventType,
    ExecutionStatus,
    MemoryScope,
    Plan,
    Task,
    TaskStatus,
)


class ScriptedProvider(MockProvider):
    """Returns a fixed plan so orchestration is deterministic in tests."""

    def __init__(self, tasks):
        super().__init__()
        self._tasks = tasks

    def plan(self, objective, context=""):
        return Plan(objective=objective, tasks=[Task(**t) for t in self._tasks])


def _orch(settings, memory, registry, provider):
    return Orchestrator(provider=provider, memory=memory, registry=registry,
                        settings=settings)


def test_reaches_end_and_emits_core_events(settings, memory, registry):
    provider = ScriptedProvider([
        {"id": "task-1", "description": "inspect", "tool": "list_dir",
         "tool_args": {"path": "."}},
    ])
    orch = _orch(settings, memory, registry, provider)
    state, result = orch.run("inspect the project")
    assert state.node == END
    types = {e.type for e in orch.events.history()}
    assert EventType.PLAN_CREATED in types
    assert EventType.TASK_STARTED in types
    assert EventType.VERIFICATION_COMPLETED in types
    assert result.status == ExecutionStatus.COMPLETED


def test_integration_objective_plan_tool_failure_recovery_success(
        settings, memory, registry):
    """THE required integration test:
    objective -> plan -> tool -> failure -> recovery -> success -> verify."""
    provider = ScriptedProvider([
        {"id": "task-1", "description": "inspect repo", "tool": "list_dir",
         "tool_args": {"path": "."}},
        {"id": "task-2", "description": "run the flaky build step",
         "tool": "flaky_build", "depends_on": ["task-1"]},
    ])
    orch = _orch(settings, memory, registry, provider)
    state, result = orch.run("Build and ship the service")

    # succeeded overall and was verified
    assert result.status == ExecutionStatus.COMPLETED
    assert result.verified is True
    assert all(t.status == TaskStatus.COMPLETED for t in state.plan.tasks)

    # the recovery path actually fired: a failure, then a retry, then success
    seq = [e.type for e in orch.events.history()]
    assert EventType.TOOL_FAILED in seq
    assert EventType.RECOVERY_STARTED in seq
    assert EventType.OBJECTIVE_COMPLETED in seq
    # failure came before the recovery, which came before completion
    assert seq.index(EventType.TOOL_FAILED) < seq.index(EventType.RECOVERY_STARTED)
    assert seq.index(EventType.RECOVERY_STARTED) < seq.index(EventType.OBJECTIVE_COMPLETED)

    # the flaky tool was attempted twice (fail then success)
    assert state.plan.get("task-2").attempts == 2

    # the experience was persisted to long-term memory
    lessons = memory.store.list(scope=MemoryScope.LONG_TERM)
    assert any("Build and ship the service" in r.content for r in lessons)


def test_recovery_is_bounded_and_fails_cleanly(settings, memory, registry):
    provider = ScriptedProvider([
        {"id": "task-1", "description": "never converges", "tool": "always_fail"},
    ])
    orch = _orch(settings, memory, registry, provider)
    state, result = orch.run("attempt the impossible")
    assert result.status == ExecutionStatus.FAILED
    # bounded: it did not loop forever; it revised the plan up to the limit
    assert state.plan_revisions <= settings.max_plan_revisions
    assert any(e.type == EventType.OBJECTIVE_FAILED for e in orch.events.history())


def test_permission_gate_pauses_then_resumes(settings, memory, registry):
    # supervised mode gates the ELEVATED write_file tool
    provider = ScriptedProvider([
        {"id": "task-1", "description": "write a file", "tool": "write_file",
         "tool_args": {"path": "note.txt", "content": "hi"}},
    ])
    perms = PermissionManager(autonomy="supervised")
    orch = Orchestrator(provider=provider, memory=memory, registry=registry,
                        settings=settings, permissions=perms)
    state, result = orch.run("write a note")
    assert state.status == ExecutionStatus.AWAITING_APPROVAL
    assert any(e.type == EventType.APPROVAL_REQUIRED for e in orch.events.history())

    # approve and resume
    state, result = orch.resume(state, approvals=["write_file"])
    assert result.status == ExecutionStatus.COMPLETED
    assert (settings_path := state.plan.get("task-1")).status == TaskStatus.COMPLETED
