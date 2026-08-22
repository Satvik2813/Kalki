"""Permission model: risk gating and approvals."""
from agent.permissions import PermissionManager
from shared.contracts import RiskLevel


def test_safe_always_allowed():
    pm = PermissionManager(autonomy="supervised")
    assert pm.check("read_file", RiskLevel.SAFE).allowed


def test_supervised_gates_elevated_until_approved():
    pm = PermissionManager(autonomy="supervised")
    d = pm.check("write_file", RiskLevel.ELEVATED)
    assert not d.allowed and d.requires_approval
    pm.approve(tool="write_file")
    assert pm.check("write_file", RiskLevel.ELEVATED).allowed


def test_autonomous_allows_elevated_but_still_gates_dangerous():
    pm = PermissionManager(autonomy="autonomous")
    assert pm.check("write_file", RiskLevel.ELEVATED).allowed
    assert not pm.check("prod_rollback", RiskLevel.DANGEROUS).allowed
