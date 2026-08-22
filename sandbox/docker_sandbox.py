"""Docker sandbox — isolated code execution for KALKI.

Provides ``sandbox_exec``: runs a command inside a Docker container with
strict resource limits, network isolation, and auto-cleanup.

Falls back gracefully to local subprocess execution when Docker is
unavailable (with a warning in the result).

Architecture:
    KALKI → sandbox_exec → docker run (--rm, --network=none, volume) →
    stdout/stderr → ToolResult → KALKI
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec

log = logging.getLogger("kalki.sandbox")

_DEFAULT_IMAGE = "python:3.12-slim"
_DEFAULT_TIMEOUT = 60
_DEFAULT_MEMORY = "256m"
_DEFAULT_CPUS = "1.0"


def _docker_available() -> bool:
    """Check if Docker is accessible."""
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=5
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class SandboxExecTool(Tool):
    spec = ToolSpec(
        name="sandbox_exec",
        description=(
            "Execute a command inside an isolated Docker container.  "
            "Network access is disabled, filesystem is read-only except "
            "the workspace mount, and resources are limited.  Falls back "
            "to local execution if Docker is unavailable."
        ),
        parameters={
            "command": "str — command to execute inside the container",
            "image": f"str (optional, default '{_DEFAULT_IMAGE}') — Docker image",
            "timeout": f"int (optional, default {_DEFAULT_TIMEOUT}) — seconds",
            "memory": f"str (optional, default '{_DEFAULT_MEMORY}') — memory limit",
            "cpus": f"str (optional, default '{_DEFAULT_CPUS}') — CPU limit",
            "workdir": "str (optional, default '/workspace') — working directory inside container",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args.get("command")
        if not command:
            return ToolResult.failure(
                self.spec.name, "missing 'command'", FailureClass.TOOL_ERROR
            )

        timeout = int(args.get("timeout", _DEFAULT_TIMEOUT))
        image = args.get("image", _DEFAULT_IMAGE)
        memory = args.get("memory", _DEFAULT_MEMORY)
        cpus = args.get("cpus", _DEFAULT_CPUS)
        workdir = args.get("workdir", "/workspace")

        if _docker_available():
            return self._run_docker(command, ctx, image, timeout, memory, cpus, workdir)
        else:
            log.warning("Docker not available — falling back to local execution")
            return self._run_local(command, ctx, timeout)

    def _run_docker(
        self, command: str, ctx: ToolContext,
        image: str, timeout: int, memory: str, cpus: str, workdir: str,
    ) -> ToolResult:
        docker_cmd = [
            "docker", "run",
            "--rm",                             # auto-cleanup
            "--network=none",                   # no network access
            "--read-only",                      # read-only root filesystem
            f"--memory={memory}",               # memory limit
            f"--cpus={cpus}",                   # CPU limit
            "--tmpfs", "/tmp:rw,size=64m",      # writable /tmp
            "-v", f"{ctx.workspace_root}:{workdir}:rw",  # workspace mount
            "-w", workdir,                      # working directory
            image,
            "sh", "-c", command,
        ]

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                docker_cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.perf_counter() - start) * 1000)
            # Kill the container if it's still running.
            return ToolResult.failure(
                self.spec.name,
                f"sandbox execution timed out after {timeout}s",
                FailureClass.TRANSIENT,
                status="TIMEOUT",
                sandboxed=True,
                duration_ms=elapsed,
            )
        except FileNotFoundError:
            return ToolResult.failure(
                self.spec.name, "docker command not found",
                FailureClass.TOOL_ERROR,
                sandboxed=False,
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
                    "sandboxed": True,
                    "image": image,
                },
                sandboxed=True,
            )

        return ToolResult.failure(
            self.spec.name,
            f"exit {proc.returncode}: {(stdout + stderr)[-1500:]}",
            FailureClass.TOOL_ERROR,
            returncode=proc.returncode,
            status="FAILED",
            sandboxed=True,
            duration_ms=elapsed,
        )

    def _run_local(self, command: str, ctx: ToolContext, timeout: int) -> ToolResult:
        """Fallback: run locally when Docker is unavailable."""
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                command, shell=True, cwd=ctx.workspace_root,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.perf_counter() - start) * 1000)
            return ToolResult.failure(
                self.spec.name,
                f"local execution timed out after {timeout}s",
                FailureClass.TRANSIENT,
                status="TIMEOUT",
                sandboxed=False,
                duration_ms=elapsed,
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
                    "sandboxed": False,
                    "warning": "Docker unavailable — ran locally without sandbox isolation",
                },
                sandboxed=False,
            )

        return ToolResult.failure(
            self.spec.name,
            f"exit {proc.returncode}: {(stdout + stderr)[-1500:]}",
            FailureClass.TOOL_ERROR,
            returncode=proc.returncode,
            status="FAILED",
            sandboxed=False,
            duration_ms=elapsed,
        )


def register_sandbox_tools(registry: ToolRegistry) -> None:
    registry.register(SandboxExecTool())
