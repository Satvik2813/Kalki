"""Git tools — local repository operations for KALKI.

Provides: ``git_status``, ``git_diff``, ``git_log``, ``git_branch``,
``git_checkout``, ``git_add``, ``git_commit``.

All operations run inside ``ctx.workspace_root``.  Push to production
branches (main/master) is blocked.
"""
from __future__ import annotations

import subprocess
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec

_PROTECTED_BRANCHES = {"main", "master", "production", "release"}


def _git(ctx: ToolContext, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command in the workspace and return the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=ctx.workspace_root,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ── git_status ───────────────────────────────────────────────────
class GitStatusTool(Tool):
    spec = ToolSpec(
        name="git_status",
        description="Show the working-tree status (branch, staged, modified, untracked).",
        parameters={},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        branch_proc = _git(ctx, "branch", "--show-current")
        status_proc = _git(ctx, "status", "--porcelain")
        if status_proc.returncode != 0:
            return ToolResult.failure(
                self.spec.name,
                f"git status failed: {status_proc.stderr}",
                FailureClass.TOOL_ERROR,
            )
        lines = [l for l in status_proc.stdout.splitlines() if l.strip()]
        staged = [l[3:] for l in lines if l[0] in "MADR"]
        modified = [l[3:] for l in lines if l[1] in "MD"]
        untracked = [l[3:] for l in lines if l.startswith("??")]
        return ToolResult.success(self.spec.name, output={
            "branch": branch_proc.stdout.strip(),
            "clean": len(lines) == 0,
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
            "raw": status_proc.stdout,
        })


# ── git_diff ─────────────────────────────────────────────────────
class GitDiffTool(Tool):
    spec = ToolSpec(
        name="git_diff",
        description="Show git diff (working tree, staged, or specific file).",
        parameters={
            "staged": "bool (optional, default false) — show staged diff",
            "file": "str (optional) — restrict to a specific file",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        cmd = ["diff"]
        if args.get("staged"):
            cmd.append("--cached")
        f = args.get("file")
        if f:
            cmd.extend(["--", f])
        proc = _git(ctx, *cmd)
        if proc.returncode != 0:
            return ToolResult.failure(
                self.spec.name, f"git diff failed: {proc.stderr}",
                FailureClass.TOOL_ERROR,
            )
        return ToolResult.success(self.spec.name, output=proc.stdout)


# ── git_log ──────────────────────────────────────────────────────
class GitLogTool(Tool):
    spec = ToolSpec(
        name="git_log",
        description="Show recent commit log.",
        parameters={"count": "int (optional, default 10) — number of commits"},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        n = str(int(args.get("count", 10)))
        proc = _git(ctx, "log", f"--oneline", f"-{n}")
        if proc.returncode != 0:
            return ToolResult.failure(
                self.spec.name, f"git log failed: {proc.stderr}",
                FailureClass.TOOL_ERROR,
            )
        commits = []
        for line in proc.stdout.strip().splitlines():
            parts = line.split(" ", 1)
            commits.append({"hash": parts[0], "message": parts[1] if len(parts) > 1 else ""})
        return ToolResult.success(self.spec.name, output=commits)


# ── git_branch ───────────────────────────────────────────────────
class GitBranchTool(Tool):
    spec = ToolSpec(
        name="git_branch",
        description="List branches or create a new branch.",
        parameters={
            "create": "str (optional) — name of new branch to create",
            "list_all": "bool (optional, default false) — include remote branches",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        create = args.get("create")
        if create:
            proc = _git(ctx, "branch", create)
            if proc.returncode != 0:
                return ToolResult.failure(
                    self.spec.name, f"branch creation failed: {proc.stderr}",
                    FailureClass.TOOL_ERROR,
                )
            return ToolResult.success(
                self.spec.name, output=f"created branch '{create}'"
            )
        # List mode.
        cmd = ["branch"]
        if args.get("list_all"):
            cmd.append("-a")
        proc = _git(ctx, *cmd)
        branches = [b.strip().lstrip("* ") for b in proc.stdout.splitlines() if b.strip()]
        current = None
        for b in proc.stdout.splitlines():
            if b.startswith("*"):
                current = b[2:].strip()
        return ToolResult.success(self.spec.name, output={
            "branches": branches, "current": current,
        })


# ── git_checkout ─────────────────────────────────────────────────
class GitCheckoutTool(Tool):
    spec = ToolSpec(
        name="git_checkout",
        description="Switch branches.",
        parameters={
            "branch": "str — branch to switch to",
            "create": "bool (optional, default false) — create if not exists (-b)",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        branch = args.get("branch")
        if not branch:
            return ToolResult.failure(
                self.spec.name, "missing 'branch'", FailureClass.TOOL_ERROR
            )
        cmd = ["checkout"]
        if args.get("create"):
            cmd.append("-b")
        cmd.append(branch)
        proc = _git(ctx, *cmd)
        if proc.returncode != 0:
            return ToolResult.failure(
                self.spec.name, f"checkout failed: {proc.stderr.strip()}",
                FailureClass.TOOL_ERROR,
            )
        return ToolResult.success(
            self.spec.name, output=f"switched to branch '{branch}'"
        )


# ── git_add ──────────────────────────────────────────────────────
class GitAddTool(Tool):
    spec = ToolSpec(
        name="git_add",
        description="Stage files for commit.",
        parameters={
            "files": "list[str] | str (default '.') — files/patterns to stage",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        files = args.get("files", ".")
        if isinstance(files, str):
            files = [files]
        proc = _git(ctx, "add", *files)
        if proc.returncode != 0:
            return ToolResult.failure(
                self.spec.name, f"git add failed: {proc.stderr}",
                FailureClass.TOOL_ERROR,
            )
        return ToolResult.success(
            self.spec.name, output=f"staged: {files}"
        )


# ── git_commit ───────────────────────────────────────────────────
class GitCommitTool(Tool):
    spec = ToolSpec(
        name="git_commit",
        description="Commit staged changes with a message.",
        parameters={"message": "str — commit message"},
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        msg = args.get("message")
        if not msg:
            return ToolResult.failure(
                self.spec.name, "missing 'message'", FailureClass.TOOL_ERROR
            )
        proc = _git(ctx, "commit", "-m", msg)
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            return ToolResult.failure(
                self.spec.name, f"commit failed: {err}",
                FailureClass.TOOL_ERROR,
            )
        return ToolResult.success(
            self.spec.name,
            output=proc.stdout.strip(),
            code_changed=True,
        )


# ── registration ─────────────────────────────────────────────────
def register_git_tools(registry: ToolRegistry) -> None:
    for cls in (
        GitStatusTool, GitDiffTool, GitLogTool, GitBranchTool,
        GitCheckoutTool, GitAddTool, GitCommitTool,
    ):
        registry.register(cls())
