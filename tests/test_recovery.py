"""Recovery engine: classification and bounded decisions."""
from agent.recovery import ABORT, ESCALATE, REPLAN, RETRY, RecoveryEngine
from shared.contracts import FailureClass, Task, ToolResult


def _failed_task(fclass, attempts):
    t = Task(id="t", description="d")
    t.attempts = attempts
    r = ToolResult.failure("tool", "boom", fclass)
    return t, r


def test_transient_within_limit_retries():
    eng = RecoveryEngine(max_task_retries=2, max_plan_revisions=3)
    t, r = _failed_task(FailureClass.TRANSIENT, attempts=1)
    assert eng.decide(t, r, plan_revisions=0).action == RETRY


def test_transient_over_limit_replans_then_aborts():
    eng = RecoveryEngine(max_task_retries=2, max_plan_revisions=1)
    t, r = _failed_task(FailureClass.TRANSIENT, attempts=3)
    assert eng.decide(t, r, plan_revisions=0).action == REPLAN
    # revisions exhausted -> abort
    assert eng.decide(t, r, plan_revisions=1).action == ABORT


def test_logic_error_replans_without_wasting_retries():
    eng = RecoveryEngine()
    t, r = _failed_task(FailureClass.LOGIC_ERROR, attempts=1)
    assert eng.decide(t, r, plan_revisions=0).action == REPLAN


def test_permission_escalates():
    eng = RecoveryEngine()
    t, r = _failed_task(FailureClass.PERMISSION, attempts=1)
    assert eng.decide(t, r, plan_revisions=0).action == ESCALATE


def test_fatal_aborts():
    eng = RecoveryEngine()
    t, r = _failed_task(FailureClass.FATAL, attempts=0)
    assert eng.decide(t, r, plan_revisions=0).action == ABORT
