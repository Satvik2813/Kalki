"""Failure recovery engine.

KALKI must not blindly retry forever. Given a failed :class:`ToolResult`, the
engine classifies the failure and chooses one of:

  * ``RETRY``    — transient/tool error, attempts remain -> try again
  * ``REPLAN``   — logic error, or retries exhausted -> revise the plan
  * ``ESCALATE`` — permission required -> pause for human approval
  * ``ABORT``    — fatal, or plan revisions exhausted -> fail the objective
"""
from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import FailureClass, Task, ToolResult

RETRY = "retry"
REPLAN = "replan"
ESCALATE = "escalate"
ABORT = "abort"


@dataclass
class RecoveryDecision:
    action: str
    reason: str
    diagnosis: str = ""


class RecoveryEngine:
    def __init__(self, max_task_retries: int = 2, max_plan_revisions: int = 3):
        self.max_task_retries = max_task_retries
        self.max_plan_revisions = max_plan_revisions

    def classify(self, result: ToolResult) -> FailureClass:
        return result.failure_class or FailureClass.UNKNOWN

    def decide(
        self, task: Task, result: ToolResult, plan_revisions: int
    ) -> RecoveryDecision:
        fclass = self.classify(result)
        diagnosis = result.error or "unknown failure"

        if fclass == FailureClass.FATAL:
            return RecoveryDecision(ABORT, "fatal failure", diagnosis)

        if fclass == FailureClass.PERMISSION:
            return RecoveryDecision(ESCALATE, "human approval required", diagnosis)

        # Transient / tool errors: retry while attempts remain.
        if fclass in (FailureClass.TRANSIENT, FailureClass.TOOL_ERROR):
            if task.attempts <= self.max_task_retries:
                return RecoveryDecision(
                    RETRY, f"{fclass.value}; attempt {task.attempts} within limit",
                    diagnosis,
                )
            # exhausted retries -> escalate to a replan
            if plan_revisions < self.max_plan_revisions:
                return RecoveryDecision(REPLAN, "retries exhausted; replanning",
                                        diagnosis)
            return RecoveryDecision(ABORT, "retries and revisions exhausted", diagnosis)

        # Logic errors: the approach is wrong -> replan (don't waste retries).
        if fclass in (FailureClass.LOGIC_ERROR, FailureClass.UNKNOWN):
            if plan_revisions < self.max_plan_revisions:
                return RecoveryDecision(REPLAN, f"{fclass.value}; revising plan",
                                        diagnosis)
            return RecoveryDecision(ABORT, "plan revisions exhausted", diagnosis)

        return RecoveryDecision(ABORT, "unhandled failure class", diagnosis)
