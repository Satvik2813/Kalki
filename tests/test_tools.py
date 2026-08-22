"""Built-in tools: sandboxing, results, and classifications."""
from agent.tools.base import ToolContext, ToolRegistry
from agent.tools.builtins import register_builtins
from shared.contracts import FailureClass


def _ctx(tmp_path):
    return ToolContext(workspace_root=str(tmp_path), run_id="run-1")


def test_write_then_read_file(tmp_path):
    reg = register_builtins(ToolRegistry())
    ctx = _ctx(tmp_path)
    w = reg.get("write_file").invoke({"path": "a/b.txt", "content": "hello"}, ctx)
    assert w.ok and w.metadata.get("code_changed")
    r = reg.get("read_file").invoke({"path": "a/b.txt"}, ctx)
    assert r.ok and r.output == "hello"


def test_path_escaping_is_blocked(tmp_path):
    reg = register_builtins(ToolRegistry())
    ctx = _ctx(tmp_path)
    res = reg.get("read_file").invoke({"path": "../../etc/passwd"}, ctx)
    assert not res.ok
    assert res.failure_class == FailureClass.TOOL_ERROR


def test_run_command_captures_failure(tmp_path):
    reg = register_builtins(ToolRegistry())
    ctx = _ctx(tmp_path)
    res = reg.get("run_command").invoke(
        {"command": "python -c \"import sys; sys.exit(3)\""}, ctx)
    assert not res.ok
    assert res.metadata.get("returncode") == 3


def test_deploy_returns_url(tmp_path):
    reg = register_builtins(ToolRegistry())
    res = reg.get("deploy").invoke({"environment": "preview"}, _ctx(tmp_path))
    assert res.ok and res.metadata.get("deploy_url")


def test_invoke_never_raises(tmp_path):
    reg = register_builtins(ToolRegistry())
    # missing required args -> classified failure, not an exception
    res = reg.get("write_file").invoke({}, _ctx(tmp_path))
    assert not res.ok and res.failure_class is not None
