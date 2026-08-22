"""Tests for the terminal execution tool (terminal_exec)."""
import sys

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass
from tools.terminal import register_terminal_tools

PY = sys.executable


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_terminal_tools(r)
    return r


def _ctx(tmp_path) -> ToolContext:
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


class TestTerminalExec:
    def test_successful_command(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": f'{PY} -c "print(42)"'}, _ctx(tmp_path)
        )
        assert res.ok
        assert "42" in res.output["stdout"]
        assert res.output["exit_code"] == 0
        assert res.output["status"] == "SUCCESS"

    def test_failed_command(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": f'{PY} -c "import sys; sys.exit(5)"'}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR
        assert res.metadata.get("returncode") == 5
        assert res.metadata.get("status") == "FAILED"

    def test_missing_command(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_blocked_destructive_command(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": "rm -rf /"}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION
        assert res.metadata.get("status") == "BLOCKED"

    def test_blocked_format_command(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": "format C:"}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_timeout(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": f'{PY} -c "import time; time.sleep(30)"', "timeout": 1},
            _ctx(tmp_path),
        )
        assert not res.ok
        assert res.failure_class == FailureClass.TRANSIENT
        assert res.metadata.get("status") == "TIMEOUT"

    def test_captures_stderr(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": f"""{PY} -c "import sys; sys.stderr.write('err\\n')" """},
            _ctx(tmp_path),
        )
        assert res.ok
        assert "err" in res.output["stderr"]

    def test_cwd_relative(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "marker.txt").write_text("found")
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": f"""{PY} -c "import os; print(os.listdir('.'))" """, "cwd": "sub"},
            _ctx(tmp_path),
        )
        assert res.ok
        assert "marker.txt" in res.output["stdout"]

    def test_cwd_sandbox_escape(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": "dir", "cwd": "../../.."}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_structured_output_fields(self, tmp_path):
        reg = _reg()
        res = reg.get("terminal_exec").invoke(
            {"command": f'{PY} -c "print(\'hi\')"'}, _ctx(tmp_path)
        )
        assert res.ok
        out = res.output
        assert "stdout" in out
        assert "stderr" in out
        assert "exit_code" in out
        assert "duration_ms" in out
        assert "status" in out
