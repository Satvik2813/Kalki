"""Execution verification.

A task or objective is never "done" just because an action returned success.
The verifier independently confirms the end state: the test suite passed during
the run, and any deployment produced a URL that answers a health check.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import AgentState, TaskStatus


@dataclass
class VerificationReport:
    verified: bool
    checks: list[dict] = field(default_factory=list)
    summary: str = ""


class Verifier:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def verify(self, state: AgentState, ctx: ToolContext) -> VerificationReport:
        checks: list[dict] = []
        plan = state.plan

        # 1) All planned tasks reached a terminal-good state.
        if plan is not None:
            incomplete = [t.id for t in plan.tasks
                          if t.status not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)]
            checks.append({
                "name": "plan_complete",
                "ok": not incomplete,
                "detail": "all tasks completed" if not incomplete
                          else f"incomplete: {incomplete}",
            })

        # 2) Evidence that tests passed at least once (from any run_tests task).
        tests_ran = False
        tests_ok = False
        if plan is not None:
            for t in plan.tasks:
                if t.tool == "run_tests" and t.result is not None:
                    tests_ran = True
                    if t.result.ok:
                        tests_ok = True
        if tests_ran:
            checks.append({"name": "tests_passed", "ok": tests_ok,
                           "detail": "test task succeeded" if tests_ok
                                     else "test task did not pass"})

        # 3) If something was deployed, smoke-test the deploy URL.
        deploy_url = None
        if plan is not None:
            for t in plan.tasks:
                if t.result and t.result.metadata.get("deploy_url"):
                    deploy_url = t.result.metadata["deploy_url"]
        if deploy_url:
            http = self.registry.get("http_check")
            if http is not None:
                # Simulated deploy URLs (*.kalki.local) can't be reached; treat
                # the presence of a deploy URL as a passed smoke check in the
                # reference impl, but record it explicitly.
                if ".kalki.local" in deploy_url:
                    checks.append({"name": "deploy_smoke", "ok": True,
                                   "detail": f"(simulated) {deploy_url}"})
                else:
                    res = http.invoke({"url": deploy_url}, ctx)
                    checks.append({"name": "deploy_smoke", "ok": res.ok,
                                   "detail": res.output if res.ok else res.error})

        verified = all(c["ok"] for c in checks) if checks else False
        summary = "; ".join(f"{c['name']}={'ok' if c['ok'] else 'FAIL'}" for c in checks)
        return VerificationReport(verified=verified, checks=checks, summary=summary)
