"""Reliability: a model/provider exception during planning must not escape the
orchestration loop — it must land in the existing FAILED terminal state with an
OBJECTIVE_FAILED event, while success, fallback, and recovery all still work.

All deterministic; mocks only; no HF / OmniRoute / paid / external calls."""
from agent.orchestrator import END, Orchestrator
from config.settings import Settings
from models.mock import MockProvider
from models.registry import get_provider
from shared.contracts import (
    EventType,
    ExecutionStatus,
    Plan,
    Task,
    TaskStatus,
)


class RaisingProvider(MockProvider):
    """Simulates a real provider failing at call time (e.g. HF DNS error)."""

    def plan(self, objective, context=""):
        raise ConnectionError("simulated provider failure: NameResolutionError")


class ScriptedProvider(MockProvider):
    def __init__(self, tasks):
        super().__init__()
        self._tasks = tasks

    def plan(self, objective, context=""):
        return Plan(objective=objective, tasks=[Task(**t) for t in self._tasks])


def _orch(settings, memory, registry, provider):
    return Orchestrator(provider=provider, memory=memory, registry=registry,
                        settings=settings)


# 1) Model success still works.
def test_model_success_still_plans(settings, memory, registry):
    provider = ScriptedProvider([
        {"id": "task-1", "description": "inspect", "tool": "list_dir",
         "tool_args": {"path": "."}},
    ])
    orch = _orch(settings, memory, registry, provider)
    state, result = orch.run("inspect the project")
    types = {e.type for e in orch.events.history()}
    assert EventType.PLAN_CREATED in types
    assert result.status == ExecutionStatus.COMPLETED
    assert state.node == END


# 2) Model exception does not crash the process.
def test_model_exception_does_not_crash(settings, memory, registry):
    orch = _orch(settings, memory, registry, RaisingProvider())
    # must return normally, not raise
    state, result = orch.run("fix the bug")
    assert state.node == END


# 3) Run transitions to the existing FAILED terminal state, error preserved.
def test_model_exception_transitions_to_failed(settings, memory, registry):
    orch = _orch(settings, memory, registry, RaisingProvider())
    state, result = orch.run("fix the bug")
    assert result.status == ExecutionStatus.FAILED
    # provider error is preserved, not hidden
    assert result.error and "ConnectionError" in result.error
    assert "CREATE_PLAN" in result.error


# 4) OBJECTIVE_FAILED is emitted.
def test_model_exception_emits_objective_failed(settings, memory, registry):
    orch = _orch(settings, memory, registry, RaisingProvider())
    orch.run("fix the bug")
    evts = [e for e in orch.events.history() if e.type == EventType.OBJECTIVE_FAILED]
    assert evts, "expected an OBJECTIVE_FAILED event"
    assert evts[0].data.get("error_type") == "ConnectionError"


# 5) Existing fallback behaviour remains intact (selection-time, unchanged).
def test_fallback_behaviour_unchanged(monkeypatch):
    import urllib.error
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError("down")),
    )
    s = Settings(model_provider="omniroute", omniroute_base_url="http://127.0.0.1:9",
                 anthropic_api_key="", openai_api_key="", huggingface_api_key="")
    assert get_provider(settings=s).name == "mock"


# 6) Existing recovery behaviour is not broken (flaky tool -> retry -> success).
def test_recovery_still_works(settings, memory, registry):
    provider = ScriptedProvider([
        {"id": "task-1", "description": "flaky build", "tool": "flaky_build"},
    ])
    orch = _orch(settings, memory, registry, provider)
    state, result = orch.run("build it")
    seq = [e.type for e in orch.events.history()]
    assert EventType.TOOL_FAILED in seq and EventType.RECOVERY_STARTED in seq
    assert result.status == ExecutionStatus.COMPLETED
    assert state.plan.get("task-1").status == TaskStatus.COMPLETED
    assert state.plan.get("task-1").attempts == 2
