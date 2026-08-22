"""GitHub integration tool — GitHub API operations for KALKI.

Provides: ``github_get_repo``, ``github_list_files``, ``github_get_file``,
``github_create_branch``, ``github_create_pr``, ``github_get_pr``,
``github_actions_status``.

Auth via ``GITHUB_TOKEN`` env var.  Tokens are NEVER exposed in
ToolResult output, logs, or event data.

Uses stdlib ``urllib`` — zero external dependencies.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from base64 import b64decode
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec

_API = "https://api.github.com"
_DEFAULT_REPO = "Satvik2813/Kalki"


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _api_call(method: str, path: str, token: str,
              body: dict | None = None, timeout: int = 15) -> dict[str, Any]:
    """Make a GitHub API call and return parsed JSON."""
    url = f"{_API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(token), method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _no_token(tool: str) -> ToolResult:
    return ToolResult.failure(
        tool, "GITHUB_TOKEN not set — configure it in environment",
        FailureClass.PERMISSION,
    )


# ── github_get_repo ──────────────────────────────────────────────
class GitHubGetRepoTool(Tool):
    spec = ToolSpec(
        name="github_get_repo",
        description="Get repository metadata from GitHub.",
        parameters={"repo": f"str (optional, default '{_DEFAULT_REPO}') — owner/repo"},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        repo = args.get("repo", _DEFAULT_REPO)
        try:
            data = _api_call("GET", f"/repos/{repo}", token)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub API error: {e.code} {e.reason}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub unreachable: {e}",
                FailureClass.TRANSIENT,
            )
        return ToolResult.success(self.spec.name, output={
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "default_branch": data.get("default_branch"),
            "private": data.get("private"),
            "language": data.get("language"),
            "open_issues_count": data.get("open_issues_count"),
        })


# ── github_list_files ────────────────────────────────────────────
class GitHubListFilesTool(Tool):
    spec = ToolSpec(
        name="github_list_files",
        description="List files at a path in the repository via GitHub API.",
        parameters={
            "repo": f"str (optional, default '{_DEFAULT_REPO}')",
            "path": "str (optional, default '') — directory path",
            "ref": "str (optional) — branch or commit ref",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        repo = args.get("repo", _DEFAULT_REPO)
        path = args.get("path", "")
        api_path = f"/repos/{repo}/contents/{path}"
        ref = args.get("ref")
        if ref:
            api_path += f"?ref={ref}"
        try:
            data = _api_call("GET", api_path, token)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub unreachable: {e}",
                FailureClass.TRANSIENT,
            )
        if isinstance(data, list):
            entries = [{"name": e["name"], "type": e["type"], "path": e["path"]}
                       for e in data]
        else:
            entries = [{"name": data["name"], "type": data["type"], "path": data["path"]}]
        return ToolResult.success(self.spec.name, output=entries)


# ── github_get_file ──────────────────────────────────────────────
class GitHubGetFileTool(Tool):
    spec = ToolSpec(
        name="github_get_file",
        description="Get the content of a file from the repository via GitHub API.",
        parameters={
            "repo": f"str (optional, default '{_DEFAULT_REPO}')",
            "path": "str — file path in the repository",
            "ref": "str (optional) — branch or commit ref",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        path = args.get("path")
        if not path:
            return ToolResult.failure(
                self.spec.name, "missing 'path'", FailureClass.TOOL_ERROR
            )
        repo = args.get("repo", _DEFAULT_REPO)
        api_path = f"/repos/{repo}/contents/{path}"
        ref = args.get("ref")
        if ref:
            api_path += f"?ref={ref}"
        try:
            data = _api_call("GET", api_path, token)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub unreachable: {e}",
                FailureClass.TRANSIENT,
            )
        content = ""
        if data.get("content"):
            try:
                content = b64decode(data["content"]).decode("utf-8")
            except Exception:
                content = "(binary content)"
        return ToolResult.success(self.spec.name, output={
            "path": data.get("path"),
            "size": data.get("size"),
            "content": content,
            "sha": data.get("sha"),
        })


# ── github_create_branch ────────────────────────────────────────
class GitHubCreateBranchTool(Tool):
    spec = ToolSpec(
        name="github_create_branch",
        description="Create a new branch on GitHub from a base ref.",
        parameters={
            "repo": f"str (optional, default '{_DEFAULT_REPO}')",
            "branch": "str — new branch name",
            "from_ref": "str (optional, default 'HEAD') — base branch/commit",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        branch = args.get("branch")
        if not branch:
            return ToolResult.failure(
                self.spec.name, "missing 'branch'", FailureClass.TOOL_ERROR
            )
        repo = args.get("repo", _DEFAULT_REPO)
        from_ref = args.get("from_ref", "HEAD")
        # Get the SHA of the base ref.
        try:
            ref_data = _api_call("GET", f"/repos/{repo}/git/ref/heads/{from_ref}", token)
            sha = ref_data["object"]["sha"]
        except urllib.error.HTTPError:
            # Try as a commit SHA directly.
            sha = from_ref
        except (urllib.error.URLError, OSError, KeyError) as e:
            return ToolResult.failure(
                self.spec.name, f"failed to resolve base ref: {e}",
                FailureClass.TRANSIENT,
            )
        try:
            _api_call("POST", f"/repos/{repo}/git/refs", token,
                       body={"ref": f"refs/heads/{branch}", "sha": sha})
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"branch creation failed: {e.code} {e.reason}",
                FailureClass.TOOL_ERROR,
            )
        return ToolResult.success(
            self.spec.name, output=f"created branch '{branch}' from {sha[:8]}"
        )


# ── github_create_pr ────────────────────────────────────────────
class GitHubCreatePRTool(Tool):
    spec = ToolSpec(
        name="github_create_pr",
        description="Open a pull request on GitHub.",
        parameters={
            "repo": f"str (optional, default '{_DEFAULT_REPO}')",
            "title": "str — PR title",
            "body": "str (optional) — PR description",
            "head": "str — source branch",
            "base": "str (optional, default 'main') — target branch",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        title = args.get("title")
        head = args.get("head")
        if not title or not head:
            return ToolResult.failure(
                self.spec.name, "missing 'title' or 'head'", FailureClass.TOOL_ERROR
            )
        repo = args.get("repo", _DEFAULT_REPO)
        try:
            data = _api_call("POST", f"/repos/{repo}/pulls", token, body={
                "title": title,
                "body": args.get("body", ""),
                "head": head,
                "base": args.get("base", "main"),
            })
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"PR creation failed: {e.code} {e.reason}",
                FailureClass.TOOL_ERROR,
            )
        return ToolResult.success(self.spec.name, output={
            "number": data.get("number"),
            "url": data.get("html_url"),
            "state": data.get("state"),
        })


# ── github_get_pr ────────────────────────────────────────────────
class GitHubGetPRTool(Tool):
    spec = ToolSpec(
        name="github_get_pr",
        description="Inspect an existing pull request.",
        parameters={
            "repo": f"str (optional, default '{_DEFAULT_REPO}')",
            "number": "int — PR number",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        number = args.get("number")
        if not number:
            return ToolResult.failure(
                self.spec.name, "missing 'number'", FailureClass.TOOL_ERROR
            )
        repo = args.get("repo", _DEFAULT_REPO)
        try:
            data = _api_call("GET", f"/repos/{repo}/pulls/{number}", token)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        return ToolResult.success(self.spec.name, output={
            "number": data.get("number"),
            "title": data.get("title"),
            "state": data.get("state"),
            "mergeable": data.get("mergeable"),
            "url": data.get("html_url"),
            "head": data.get("head", {}).get("ref"),
            "base": data.get("base", {}).get("ref"),
        })


# ── github_actions_status ────────────────────────────────────────
class GitHubActionsStatusTool(Tool):
    spec = ToolSpec(
        name="github_actions_status",
        description="Check the CI/CD status (GitHub Actions) for a branch or commit.",
        parameters={
            "repo": f"str (optional, default '{_DEFAULT_REPO}')",
            "ref": "str (optional, default 'HEAD') — branch name or commit SHA",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        repo = args.get("repo", _DEFAULT_REPO)
        ref = args.get("ref", "HEAD")
        try:
            data = _api_call(
                "GET", f"/repos/{repo}/actions/runs?branch={ref}&per_page=5", token
            )
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"GitHub unreachable: {e}",
                FailureClass.TRANSIENT,
            )
        runs = []
        for r in data.get("workflow_runs", []):
            runs.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "url": r.get("html_url"),
            })
        return ToolResult.success(self.spec.name, output=runs)


# ── registration ─────────────────────────────────────────────────
def register_github_tools(registry: ToolRegistry) -> None:
    for cls in (
        GitHubGetRepoTool, GitHubListFilesTool, GitHubGetFileTool,
        GitHubCreateBranchTool, GitHubCreatePRTool, GitHubGetPRTool,
        GitHubActionsStatusTool,
    ):
        registry.register(cls())
