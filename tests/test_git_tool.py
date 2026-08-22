"""Tests for git tools (git_status, git_diff, git_log, git_branch, git_checkout, git_add, git_commit)."""
import subprocess
from pathlib import Path

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass
from tools.git_tool import register_git_tools


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_git_tools(r)
    return r


def _git_workspace(tmp_path) -> ToolContext:
    """Create a git repo in tmp_path with one commit."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@kalki.local"],
                   cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "KALKI Test"],
                   cwd=str(tmp_path), capture_output=True)
    (tmp_path / "init.txt").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"],
                   cwd=str(tmp_path), capture_output=True)
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


class TestGitStatus:
    def test_clean_repo(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_status").invoke({}, ctx)
        assert res.ok
        assert res.output["clean"] is True

    def test_modified_repo(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        (tmp_path / "new.txt").write_text("new content")
        reg = _reg()
        res = reg.get("git_status").invoke({}, ctx)
        assert res.ok
        assert res.output["clean"] is False
        assert len(res.output["untracked"]) >= 1


class TestGitDiff:
    def test_diff_with_changes(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        (tmp_path / "init.txt").write_text("changed")
        reg = _reg()
        res = reg.get("git_diff").invoke({}, ctx)
        assert res.ok
        assert "changed" in res.output

    def test_diff_no_changes(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_diff").invoke({}, ctx)
        assert res.ok
        assert res.output.strip() == ""


class TestGitLog:
    def test_log_shows_commits(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_log").invoke({"count": 5}, ctx)
        assert res.ok
        assert len(res.output) >= 1
        assert "initial commit" in res.output[0]["message"]


class TestGitBranch:
    def test_create_branch(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_branch").invoke({"create": "feature/test"}, ctx)
        assert res.ok
        assert "feature/test" in res.output

    def test_list_branches(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_branch").invoke({}, ctx)
        assert res.ok
        assert len(res.output["branches"]) >= 1


class TestGitCheckout:
    def test_checkout_branch(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        reg.get("git_branch").invoke({"create": "dev"}, ctx)
        res = reg.get("git_checkout").invoke({"branch": "dev"}, ctx)
        assert res.ok

    def test_checkout_missing_branch(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_checkout").invoke({"branch": "nonexistent"}, ctx)
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_checkout_missing_arg(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_checkout").invoke({}, ctx)
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


class TestGitAdd:
    def test_add_files(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        (tmp_path / "new.txt").write_text("new")
        reg = _reg()
        res = reg.get("git_add").invoke({"files": "new.txt"}, ctx)
        assert res.ok


class TestGitCommit:
    def test_commit_staged(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        (tmp_path / "file.txt").write_text("data")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        reg = _reg()
        res = reg.get("git_commit").invoke({"message": "test commit"}, ctx)
        assert res.ok
        assert res.metadata.get("code_changed") is True

    def test_commit_missing_message(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_commit").invoke({}, ctx)
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_commit_nothing_staged(self, tmp_path):
        ctx = _git_workspace(tmp_path)
        reg = _reg()
        res = reg.get("git_commit").invoke({"message": "empty"}, ctx)
        assert not res.ok
