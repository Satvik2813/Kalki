"""Terminal execution tool — safe subprocess runner for KALKI.

Provides ``terminal_exec``: executes a command inside the workspace,
captures stdout/stderr/exit_code/duration, and returns a structured
``ToolResult``.  Destructive host commands are blocklisted.
"""
from __future__ import annotations

import re
import subprocess
import time
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec

# Commands that must never be run (case-insensitive patterns).
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brm\s+(-\w+\s+)*-rf\s+/\s*$", re.IGNORECASE),
    re.compile(r"\brm\s+(-\w+\s+)*-rf\s+~", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
    re.compile(r"\bdel\s+/[sS]", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+.+of=/dev/", re.IGNORECASE),
    re.compile(r"\b:(){ :\|:& };:", re.IGNORECASE),  # fork bomb
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\binit\s+0\b", re.IGNORECASE),
]


def _is_blocked(command: str) -> bool:
    """Return True if *command* matches any blocklist pattern."""
    return any(p.search(command) for p in _BLOCKED_PATTERNS)


class TerminalExecTool(Tool):
    spec = ToolSpec(
        name="terminal_exec",
        description=(
            "Execute a shell command in the workspace directory.  Captures "
            "stdout, stderr, exit code, and duration.  Destructive host "
            "commands are blocked."
        ),
        parameters={
            "command": "str — the shell command to run",
            "timeout": "int (optional, default 120) — seconds before timeout",
            "cwd": "str (optional) — relative subdirectory to run in",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args.get("command")
        if not command:
            return ToolResult.failure(
                self.spec.name, "missing 'command'", FailureClass.TOOL_ERROR
            )

        if _is_blocked(command):
            return ToolResult.failure(
                self.spec.name,
                f"command blocked by safety policy: {command!r}",
                FailureClass.PERMISSION,
                status="BLOCKED",
            )

        timeout = int(args.get("timeout", 120))
        cwd = ctx.workspace_root
        sub = args.get("cwd")
        if sub:
            from pathlib import Path

            resolved = (Path(cwd) / sub).resolve()
            root = Path(cwd).resolve()
            if root != resolved and root not in resolved.parents:
                return ToolResult.failure(
                    self.spec.name,
                    f"cwd {sub!r} escapes workspace sandbox",
                    FailureClass.PERMISSION,
                    status="BLOCKED",
                )
            cwd = str(resolved)

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.perf_counter() - start) * 1000)
            return ToolResult.failure(
                self.spec.name,
                f"command timed out after {timeout}s",
                FailureClass.TRANSIENT,
                status="TIMEOUT",
                duration_ms=elapsed,
            )
        except FileNotFoundError as e:
            return ToolResult.failure(
                self.spec.name,
                f"command not found: {e}",
                FailureClass.TOOL_ERROR,
                status="FAILED",
            )

        elapsed = int((time.perf_counter() - start) * 1000)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        if proc.returncode == 0:
            return ToolResult.success(
                self.spec.name,
                output={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": 0,
                    "duration_ms": elapsed,
                    "status": "SUCCESS",
                },
                returncode=0,
                status="SUCCESS",
            )

        # Trim large outputs to keep ToolResult manageable.
        combined = (stdout + stderr)[-2000:]
        return ToolResult.failure(
            self.spec.name,
            f"exit {proc.returncode}: {combined}",
            FailureClass.TOOL_ERROR,
            returncode=proc.returncode,
            status="FAILED",
            stdout=stdout[-1000:],
            stderr=stderr[-1000:],
            duration_ms=elapsed,
        )


def register_terminal_tools(registry: ToolRegistry) -> None:
    registry.register(TerminalExecTool())
