"""Planning engine.

Turns an objective into a structured :class:`Plan`, and *revises* the plan
when tool results demand it. Retrieved long-term memories are injected into the
planning context so past incidents/fixes influence the plan — satisfying the
"memory must influence decisions" requirement.
"""
from __future__ import annotations

from typing import Optional

from memory.manager import MemoryManager
from models.base import ModelProvider
from shared.contracts import (
    MemoryResult,
    Plan,
    Task,
    TaskStatus,
    new_id,
)


class Planner:
    def __init__(self, provider: ModelProvider, memory: Optional[MemoryManager] = None):
        self.provider = provider
        self.memory = memory

    # -- initial planning ----------------------------------------
    def create_plan(
        self, objective: str, project: Optional[str] = None, user_id: Optional[str] = None
    ) -> tuple[Plan, list[MemoryResult]]:
        recalled: list[MemoryResult] = []
        context = ""
        if self.memory:
            recalled = self.memory.recall_experience(objective, project=project, user_id=user_id)
            if recalled:
                lines = [f"- ({m.score:.2f}) {m.record.content}" for m in recalled]
                context = "Relevant past engineering experience:\n" + "\n".join(lines)
        plan = self.provider.plan(objective, context=context)
        return plan, recalled

    # -- dynamic replanning --------------------------------------
    def revise_after_failure(self, plan: Plan, failed: Task, diagnosis: str) -> Plan:
        """Insert a remediation task before the failed one and reset it to
        pending so the loop retries with new information. Bumps the revision."""
        plan.revision += 1
        remediation = Task(
            id=new_id("task"),
            description=f"Diagnose and remediate: {diagnosis}",
            tool=self._remediation_tool(failed),
            metadata={"generated_by": "replan", "for_task": failed.id},
        )
        # Reset the failed task so it can be attempted again after remediation.
        failed.status = TaskStatus.PENDING
        failed.error = None
        remediation_deps = list(failed.depends_on)
        remediation.depends_on = remediation_deps
        failed.depends_on = [remediation.id]

        idx = plan.tasks.index(failed)
        plan.tasks.insert(idx, remediation)
        return plan

    @staticmethod
    def _remediation_tool(failed: Task) -> Optional[str]:
        # If a code/test task failed, the remediation is typically a code edit.
        if failed.tool in ("run_tests", "http_check", "deploy"):
            return "write_file"
        return failed.tool
