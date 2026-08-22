"""Tests for GitHub integration tools (mocked — no real API calls).

All API calls are intercepted via monkeypatching urllib so tests run
offline with no GITHUB_TOKEN needed.
"""
import json
import os
from unittest.mock import patch, MagicMock
from base64 import b64encode

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass
from integrations.github_tool import register_github_tools, _api_call


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_github_tools(r)
    return r


def _ctx(tmp_path) -> ToolContext:
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


def _with_token(monkeypatch):
    """Set a fake GITHUB_TOKEN for testing."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_fake_12345")


def _mock_api(return_value):
    """Create a mock for _api_call that returns given data."""
    return patch("integrations.github_tool._api_call", return_value=return_value)


class TestGitHubGetRepo:
    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("github_get_repo").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {
            "name": "Kalki", "full_name": "Satvik2813/Kalki",
            "description": "Autonomous AI Engineer", "default_branch": "main",
            "private": False, "language": "Python", "open_issues_count": 0,
        }
        with _mock_api(mock_data):
            reg = _reg()
            res = reg.get("github_get_repo").invoke({}, _ctx(tmp_path))
        assert res.ok
        assert res.output["name"] == "Kalki"


class TestGitHubListFiles:
    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = [
            {"name": "README.md", "type": "file", "path": "README.md"},
            {"name": "agent", "type": "dir", "path": "agent"},
        ]
        with _mock_api(mock_data):
            reg = _reg()
            res = reg.get("github_list_files").invoke({}, _ctx(tmp_path))
        assert res.ok
        assert len(res.output) == 2

    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("github_list_files").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION


class TestGitHubGetFile:
    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        content = b64encode(b"print('hello')").decode()
        mock_data = {
            "path": "hello.py", "size": 14,
            "content": content + "\n", "sha": "abc123",
        }
        with _mock_api(mock_data):
            reg = _reg()
            res = reg.get("github_get_file").invoke(
                {"path": "hello.py"}, _ctx(tmp_path)
            )
        assert res.ok
        assert "print" in res.output["content"]

    def test_missing_path(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("github_get_file").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


class TestGitHubCreateBranch:
    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("github_create_branch").invoke(
            {"branch": "feature/test"}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_missing_branch(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("github_create_branch").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


class TestGitHubCreatePR:
    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {"number": 42, "html_url": "https://github.com/...", "state": "open"}
        with _mock_api(mock_data):
            reg = _reg()
            res = reg.get("github_create_pr").invoke(
                {"title": "Fix bug", "head": "dev", "base": "main"},
                _ctx(tmp_path),
            )
        assert res.ok
        assert res.output["number"] == 42

    def test_missing_args(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("github_create_pr").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


class TestGitHubGetPR:
    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("github_get_pr").invoke({"number": 1}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_missing_number(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("github_get_pr").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


class TestGitHubActionsStatus:
    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {"workflow_runs": [{
            "id": 1, "name": "CI", "status": "completed",
            "conclusion": "success", "html_url": "https://...",
        }]}
        with _mock_api(mock_data):
            reg = _reg()
            res = reg.get("github_actions_status").invoke({}, _ctx(tmp_path))
        assert res.ok
        assert len(res.output) == 1
        assert res.output[0]["conclusion"] == "success"


class TestGitHubSearchRepos:
    def test_no_token(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        reg = _reg()
        res = reg.get("github_search_repos").invoke({"query": "test"}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_missing_query(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        reg = _reg()
        res = reg.get("github_search_repos").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_success(self, tmp_path, monkeypatch):
        _with_token(monkeypatch)
        mock_data = {"items": [{
            "name": "Kalki", "full_name": "Satvik2813/Kalki",
            "description": "AI Engineer", "html_url": "https://github.com/...",
        }]}
        with _mock_api(mock_data):
            reg = _reg()
            res = reg.get("github_search_repos").invoke({"query": "kalki"}, _ctx(tmp_path))
        assert res.ok
        assert len(res.output) == 1
        assert res.output[0]["name"] == "Kalki"
