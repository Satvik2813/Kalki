"""Tests for Vercel deployment tools (mocked — no real API calls)."""
from unittest.mock import patch

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel
from integrations.vercel_tool import register_vercel_tools


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_vercel_tools(r)
    return r


def _ctx(tmp_path) -> ToolContext:
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


def _with_token(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "vercel_test_token_fake")


def _mock_vercel(return_value):
    return patch("integrations.vercel_tool._vercel_call", return_value=return_value)


class TestVercelDeploy:
    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("vercel_deploy").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {
            "id": "dpl_123", "url": "kalki-preview.vercel.app",
            "readyState": "QUEUED",
        }
        with _mock_vercel(mock_data):
            reg = _reg()
            res = reg.get("vercel_deploy").invoke(
                {"target": "preview"}, _ctx(tmp_path)
            )
        assert res.ok
        assert res.output["id"] == "dpl_123"
        assert "vercel.app" in res.output["url"]
        assert res.metadata.get("deploy_url")

    def test_risk_level(self):
        reg = _reg()
        assert reg.get("vercel_deploy").spec.risk == RiskLevel.ELEVATED


class TestVercelStatus:
    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("vercel_status").invoke(
            {"deployment_id": "dpl_123"}, _ctx(tmp_path)
        )
        assert not res.ok

    def test_missing_id(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("vercel_status").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {
            "id": "dpl_123", "readyState": "READY",
            "url": "kalki.vercel.app", "createdAt": "2026-08-22",
        }
        with _mock_vercel(mock_data):
            reg = _reg()
            res = reg.get("vercel_status").invoke(
                {"deployment_id": "dpl_123"}, _ctx(tmp_path)
            )
        assert res.ok
        assert res.output["state"] == "READY"


class TestVercelLogs:
    def test_missing_id(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("vercel_logs").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = [{"text": "Building..."}, {"text": "Ready"}]
        with _mock_vercel(mock_data):
            reg = _reg()
            res = reg.get("vercel_logs").invoke(
                {"deployment_id": "dpl_123"}, _ctx(tmp_path)
            )
        assert res.ok
        assert res.output["log_count"] == 2


class TestVercelRedeploy:
    def test_missing_id(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("vercel_redeploy").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {
            "id": "dpl_456", "url": "kalki-new.vercel.app",
            "readyState": "QUEUED",
        }
        with _mock_vercel(mock_data):
            reg = _reg()
            res = reg.get("vercel_redeploy").invoke(
                {"deployment_id": "dpl_123"}, _ctx(tmp_path)
            )
        assert res.ok
        assert res.output["id"] == "dpl_456"
