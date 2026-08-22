"""Built-in reference tools.

Minimal, safe, sandboxed implementations so KALKI has a working toolbelt:
  * read_file / write_file / list_dir  — filesystem, sandboxed to workspace_root
  * run_command / run_tests            — subprocess execution
  * http_check                         — HTTP health/smoke check (urllib)
  * deploy                             — simulated deploy (ELEVATED risk)

Dev 3 replaces/extends these with richer implementations via the registry;
the engine only depends on the Tool interface, not these concretes.
"""
from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec


def _resolve_in_sandbox(ctx: ToolContext, rel: str) -> Path:
    root = Path(ctx.workspace_root).resolve()
    target = (root / rel).resolve()
    if root != target and root not in target.parents:
        raise PermissionError(f"path {rel!r} escapes workspace sandbox")
    return target


class ReadFileTool(Tool):
    spec = ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file within the workspace.",
        parameters={"path": "str (relative to workspace)"},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not path:
            return ToolResult.failure(self.spec.name, "missing 'path'",
                                      FailureClass.TOOL_ERROR)
        target = _resolve_in_sandbox(ctx, path)
        if not target.is_file():
            return ToolResult.failure(self.spec.name, f"not found: {path}",
                                      FailureClass.TOOL_ERROR)
        return ToolResult.success(self.spec.name,
                                  output=target.read_text(encoding="utf-8"))


class ListDirTool(Tool):
    spec = ToolSpec(
        name="list_dir",
        description="List entries of a directory within the workspace.",
        parameters={"path": "str (relative, default '.')"},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = _resolve_in_sandbox(ctx, args.get("path", "."))
        if not target.is_dir():
            return ToolResult.failure(self.spec.name, "not a directory",
                                      FailureClass.TOOL_ERROR)
        entries = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
        return ToolResult.success(self.spec.name, output=entries)


class WriteFileTool(Tool):
    spec = ToolSpec(
        name="write_file",
        description="Create or overwrite a text file within the workspace.",
        parameters={"path": "str", "content": "str"},
        risk=RiskLevel.ELEVATED,  # mutates the working tree
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path, content = args.get("path"), args.get("content", "")
        if not path:
            return ToolResult.failure(self.spec.name, "missing 'path'",
                                      FailureClass.TOOL_ERROR)
        target = _resolve_in_sandbox(ctx, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult.success(self.spec.name,
                                  output=f"wrote {len(content)} bytes to {path}",
                                  code_changed=True)


class RunCommandTool(Tool):
    spec = ToolSpec(
        name="run_command",
        description="Run a shell command in the workspace and capture output.",
        parameters={"command": "str", "timeout": "int seconds (default 120)"},
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args.get("command")
        if not command:
            return ToolResult.failure(self.spec.name, "missing 'command'",
                                      FailureClass.TOOL_ERROR)
        timeout = int(args.get("timeout", 120))
        try:
            proc = subprocess.run(
                command, shell=True, cwd=ctx.workspace_root, capture_output=True,
                text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure(self.spec.name, "command timed out",
                                      FailureClass.TRANSIENT)
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            return ToolResult.success(self.spec.name, output=out,
                                      returncode=0)
        return ToolResult.failure(
            self.spec.name, f"exit {proc.returncode}: {out[-500:]}",
            FailureClass.TOOL_ERROR, returncode=proc.returncode,
        )


class RunTestsTool(Tool):
    spec = ToolSpec(
        name="run_tests",
        description="Run the project's test command (default: pytest).",
        parameters={"command": "str (default 'pytest -q')"},
        risk=RiskLevel.SAFE,  # read-only validation
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args.get("command", "pytest -q")
        try:
            proc = subprocess.run(
                command, shell=True, cwd=ctx.workspace_root, capture_output=True,
                text=True, timeout=int(args.get("timeout", 300)),
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure(self.spec.name, "tests timed out",
                                      FailureClass.TRANSIENT)
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            return ToolResult.success(self.spec.name, output=out, tests_passed=True)
        return ToolResult.failure(self.spec.name, f"tests failed:\n{out[-800:]}",
                                  FailureClass.LOGIC_ERROR, tests_passed=False)


class HttpCheckTool(Tool):
    spec = ToolSpec(
        name="http_check",
        description="HTTP GET a URL and assert a 2xx/3xx status (health/smoke).",
        parameters={"url": "str", "expect_status": "int (default any 2xx/3xx)"},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = args.get("url")
        if not url:
            return ToolResult.failure(self.spec.name, "missing 'url'",
                                      FailureClass.TOOL_ERROR)
        try:
            with urllib.request.urlopen(url, timeout=int(args.get("timeout", 10))) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
        except (urllib.error.URLError, OSError, ValueError) as e:
            return ToolResult.failure(self.spec.name, f"unreachable: {e}",
                                      FailureClass.TRANSIENT)
        expect = args.get("expect_status")
        ok = (status == expect) if expect else (200 <= status < 400)
        if ok:
            return ToolResult.success(self.spec.name, output={"status": status})
        return ToolResult.failure(self.spec.name, f"unexpected status {status}",
                                  FailureClass.LOGIC_ERROR, status=status)


class DeployTool(Tool):
    spec = ToolSpec(
        name="deploy",
        description="Deploy to a preview environment (simulated reference impl).",
        parameters={"environment": "str (default 'preview')"},
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        env = args.get("environment", "preview")
        # Reference implementation: simulate a successful preview deploy and
        # return a URL a verification step can smoke-test.
        url = f"https://{env}.kalki.local/{ctx.run_id or 'run'}"
        return ToolResult.success(self.spec.name,
                                  output={"environment": env, "url": url},
                                  deploy_url=url)


def register_builtins(registry: ToolRegistry) -> ToolRegistry:
    for tool_cls in (
        ReadFileTool, ListDirTool, WriteFileTool, RunCommandTool,
        RunTestsTool, HttpCheckTool, DeployTool,
    ):
        registry.register(tool_cls())
    return registry
