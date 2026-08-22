"""Planner: decomposition, memory-informed context, and replanning."""
from agent.planner import Planner
from models.mock import MockProvider
from shared.contracts import TaskStatus


def test_plan_decomposes_bug_objective():
    planner = Planner(MockProvider())
    plan, recalled = planner.create_plan("Fix the authentication bug and deploy it")
    descriptions = " ".join(t.description.lower() for t in plan.tasks)
    assert "inspect" in descriptions
    assert any(t.tool == "run_tests" for t in plan.tasks)
    assert any(t.tool == "deploy" for t in plan.tasks)
    assert recalled == []  # no memory manager attached


def test_plan_context_includes_recalled_memory(memory):
    memory.record_experience(
        "Auth bug was caused by an expired JWT signing key; rotating it fixed it.",
        tags=["auth", "fix"],
    )
    planner = Planner(MockProvider(), memory)
    plan, recalled = planner.create_plan("Fix the authentication bug")
    assert len(recalled) >= 1
    assert "jwt" in recalled[0].record.content.lower()


def test_revise_after_failure_inserts_remediation(memory):
    planner = Planner(MockProvider(), memory)
    plan, _ = planner.create_plan("Fix the authentication bug")
    failed = next(t for t in plan.tasks if t.tool == "run_tests")
    failed.status = TaskStatus.FAILED
    before = len(plan.tasks)
    planner.revise_after_failure(plan, failed, "tests still red")
    assert len(plan.tasks) == before + 1
    assert plan.revision == 1
    # failed task reset to pending and now depends on the remediation task
    assert failed.status == TaskStatus.PENDING
    remediation = plan.get(failed.depends_on[0])
    assert remediation is not None and "remediate" in remediation.description.lower()
