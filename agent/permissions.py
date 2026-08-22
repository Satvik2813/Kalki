"""Permission / safety model.

KALKI performs *safe* development actions autonomously and gates *high-risk*
ones behind human approval. A tool declares a :class:`RiskLevel`; the
:class:`PermissionManager` decides — from the autonomy mode and any explicit
approvals — whether an action may run now or must pause the run in
``AWAITING_APPROVAL``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from shared.contracts import RiskLevel


@dataclass
class PermissionDecision:
    allowed: bool
    requires_approval: bool = False
    reason: str = ""


@dataclass
class PermissionManager:
    """autonomy: 'supervised' (gate elevated+dangerous) or 'autonomous'
    (auto-allow safe+elevated, still gate dangerous)."""

    autonomy: str = "supervised"
    approved_tools: set[str] = field(default_factory=set)
    approved_risks: set[RiskLevel] = field(default_factory=set)

    def approve(self, *, tool: str | None = None, risk: RiskLevel | None = None) -> None:
        if tool:
            self.approved_tools.add(tool)
        if risk:
            self.approved_risks.add(risk)

    def check(self, tool_name: str, risk: RiskLevel) -> PermissionDecision:
        if risk == RiskLevel.SAFE:
            return PermissionDecision(allowed=True, reason="safe action")

        if tool_name in self.approved_tools or risk in self.approved_risks:
            return PermissionDecision(allowed=True, reason="explicitly approved")

        if risk == RiskLevel.ELEVATED and self.autonomy == "autonomous":
            return PermissionDecision(allowed=True, reason="autonomous mode")

        # Dangerous actions always require approval; elevated does too under
        # supervised mode.
        return PermissionDecision(
            allowed=False,
            requires_approval=True,
            reason=f"{risk.value} action requires human approval",
        )
