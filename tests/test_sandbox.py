"""Tests for Docker sandbox tool.

Tests run via local fallback mode (Docker may not be available in CI).
Docker-specific behaviour is tested via mocking.
"""
import sys
from unittest.mock import patch, MagicMock
import subprocess

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel
from sandbox.docker_sandbox import register_sandbox_tools, _docker_available


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_sandbox_tools(r)
    return r


def _ctx(tmp_path) -> ToolContext:
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


class TestSandboxExec:
    def test_missing_command(self, tmp_path):
        reg = _reg()
        res = reg.get("sandbox_exec").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_successful_local_fallback(self, tmp_path):
        """When Docker is unavailable, sandbox falls back to local exec."""
        with patch("sandbox.docker_sandbox._docker_available", return_value=False):
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": f'{sys.executable} -c "print(\'hello sandbox\')"'},
                _ctx(tmp_path),
            )
        assert res.ok
        assert "hello sandbox" in res.output["stdout"]
        assert res.output["sandboxed"] is False

    def test_local_fallback_warning(self, tmp_path):
        with patch("sandbox.docker_sandbox._docker_available", return_value=False):
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": f'{sys.executable} -c "print(\'test\')"'},
                _ctx(tmp_path),
            )
        assert res.ok
        assert "warning" in res.output or res.metadata.get("sandboxed") is False

    def test_local_fallback_failure(self, tmp_path):
        with patch("sandbox.docker_sandbox._docker_available", return_value=False):
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": f'{sys.executable} -c "import sys; sys.exit(1)"'},
                _ctx(tmp_path),
            )
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_local_fallback_timeout(self, tmp_path):
        with patch("sandbox.docker_sandbox._docker_available", return_value=False):
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": f'{sys.executable} -c "import time; time.sleep(30)"', "timeout": 1},
                _ctx(tmp_path),
            )
        assert not res.ok
        assert res.failure_class == FailureClass.TRANSIENT
        assert res.metadata.get("status") == "TIMEOUT"

    def test_docker_mode_success(self, tmp_path):
        """Verify Docker invocation builds the correct command."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "docker output"
        mock_proc.stderr = ""

        with patch("sandbox.docker_sandbox._docker_available", return_value=True), \
             patch("subprocess.run", return_value=mock_proc) as mock_run:
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": "echo hello", "image": "node:18-slim"},
                _ctx(tmp_path),
            )

        assert res.ok
        assert res.output["sandboxed"] is True
        # Verify docker run was called with correct flags.
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args[0]
        assert "--rm" in call_args
        assert "--network=none" in call_args
        assert "--read-only" in call_args

    def test_docker_mode_timeout(self, tmp_path):
        with patch("sandbox.docker_sandbox._docker_available", return_value=True), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": "sleep 30", "timeout": 5},
                _ctx(tmp_path),
            )
        assert not res.ok
        assert res.failure_class == FailureClass.TRANSIENT
        assert res.metadata.get("sandboxed") is True

    def test_risk_level_elevated(self):
        reg = _reg()
        assert reg.get("sandbox_exec").spec.risk == RiskLevel.ELEVATED

    def test_structured_output(self, tmp_path):
        with patch("sandbox.docker_sandbox._docker_available", return_value=False):
            reg = _reg()
            res = reg.get("sandbox_exec").invoke(
                {"command": f'{sys.executable} -c "print(\'structured\')"'},
                _ctx(tmp_path),
            )
        if res.ok:
            out = res.output
            assert "stdout" in out
            assert "stderr" in out
            assert "exit_code" in out
            assert "duration_ms" in out
            assert "status" in out
            assert "sandboxed" in out
