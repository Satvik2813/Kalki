"""Tests for the filesystem tools (fs_read, fs_write, fs_edit, fs_list, fs_search)."""
from pathlib import Path

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass
from tools.filesystem import register_filesystem_tools


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_filesystem_tools(r)
    return r


def _ctx(tmp_path) -> ToolContext:
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


# ── fs_write ─────────────────────────────────────────────────────
class TestFsWrite:
    def test_write_creates_file(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_write").invoke(
            {"path": "hello.txt", "content": "hello world"}, _ctx(tmp_path)
        )
        assert res.ok
        assert (tmp_path / "hello.txt").read_text() == "hello world"
        assert res.metadata.get("code_changed") is True

    def test_write_creates_subdirs(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_write").invoke(
            {"path": "a/b/c.txt", "content": "nested"}, _ctx(tmp_path)
        )
        assert res.ok
        assert (tmp_path / "a" / "b" / "c.txt").read_text() == "nested"

    def test_write_missing_path(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_write").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_write_sandbox_escape(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_write").invoke(
            {"path": "../../evil.txt", "content": "x"}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION


# ── fs_read ──────────────────────────────────────────────────────
class TestFsRead:
    def test_read_existing(self, tmp_path):
        (tmp_path / "data.txt").write_text("line1\nline2\nline3\n")
        reg = _reg()
        res = reg.get("fs_read").invoke({"path": "data.txt"}, _ctx(tmp_path))
        assert res.ok
        assert "line1" in res.output

    def test_read_line_range(self, tmp_path):
        (tmp_path / "data.txt").write_text("A\nB\nC\nD\n")
        reg = _reg()
        res = reg.get("fs_read").invoke(
            {"path": "data.txt", "start_line": 2, "end_line": 3}, _ctx(tmp_path)
        )
        assert res.ok
        assert res.output.strip() == "B\nC"

    def test_read_not_found(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_read").invoke({"path": "nope.txt"}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_read_sandbox_escape(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_read").invoke(
            {"path": "../../../etc/passwd"}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION


# ── fs_edit ──────────────────────────────────────────────────────
class TestFsEdit:
    def test_edit_replace_text(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\ny = 2\n")
        reg = _reg()
        res = reg.get("fs_edit").invoke(
            {"path": "app.py", "old_text": "x = 1", "new_text": "x = 42"},
            _ctx(tmp_path),
        )
        assert res.ok
        assert "x = 42" in (tmp_path / "app.py").read_text()
        assert res.metadata.get("code_changed") is True

    def test_edit_line_range(self, tmp_path):
        (tmp_path / "cfg.txt").write_text("a\nb\nc\nd\n")
        reg = _reg()
        res = reg.get("fs_edit").invoke(
            {"path": "cfg.txt", "start_line": 2, "end_line": 3, "new_text": "REPLACED"},
            _ctx(tmp_path),
        )
        assert res.ok
        content = (tmp_path / "cfg.txt").read_text()
        assert "REPLACED" in content
        assert "b" not in content
        assert "c" not in content

    def test_edit_old_text_not_found(self, tmp_path):
        (tmp_path / "f.txt").write_text("hello")
        reg = _reg()
        res = reg.get("fs_edit").invoke(
            {"path": "f.txt", "old_text": "NOPE", "new_text": "x"},
            _ctx(tmp_path),
        )
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_edit_requires_mode(self, tmp_path):
        (tmp_path / "f.txt").write_text("hello")
        reg = _reg()
        res = reg.get("fs_edit").invoke(
            {"path": "f.txt", "new_text": "x"}, _ctx(tmp_path)
        )
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


# ── fs_list ──────────────────────────────────────────────────────
class TestFsList:
    def test_list_flat(self, tmp_path):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.py").touch()
        (tmp_path / "sub").mkdir()
        reg = _reg()
        res = reg.get("fs_list").invoke({"path": "."}, _ctx(tmp_path))
        assert res.ok
        names = [e["path"] for e in res.output]
        assert "a.txt" in names

    def test_list_recursive(self, tmp_path):
        (tmp_path / "d").mkdir()
        (tmp_path / "d" / "inner.py").touch()
        reg = _reg()
        res = reg.get("fs_list").invoke(
            {"path": ".", "recursive": True}, _ctx(tmp_path)
        )
        assert res.ok
        paths = [e["path"] for e in res.output]
        assert any("inner.py" in p for p in paths)

    def test_list_glob_filter(self, tmp_path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.txt").touch()
        reg = _reg()
        res = reg.get("fs_list").invoke(
            {"path": ".", "recursive": True, "pattern": "*.py"}, _ctx(tmp_path)
        )
        assert res.ok
        assert all(e["path"].endswith(".py") for e in res.output)

    def test_list_not_a_directory(self, tmp_path):
        (tmp_path / "f.txt").touch()
        reg = _reg()
        res = reg.get("fs_list").invoke({"path": "f.txt"}, _ctx(tmp_path))
        assert not res.ok

    def test_list_sandbox_escape(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_list").invoke({"path": "../../.."}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION


# ── fs_search ────────────────────────────────────────────────────
class TestFsSearch:
    def test_search_finds_text(self, tmp_path):
        (tmp_path / "code.py").write_text("def hello():\n    pass\n")
        reg = _reg()
        res = reg.get("fs_search").invoke(
            {"query": "def hello"}, _ctx(tmp_path)
        )
        assert res.ok
        assert len(res.output) >= 1
        assert res.output[0]["line"] == 1

    def test_search_regex(self, tmp_path):
        (tmp_path / "data.py").write_text("x = 42\ny = 99\nz = 42\n")
        reg = _reg()
        res = reg.get("fs_search").invoke(
            {"query": r"\d{2}", "is_regex": True}, _ctx(tmp_path)
        )
        assert res.ok
        assert len(res.output) >= 2

    def test_search_no_results(self, tmp_path):
        (tmp_path / "empty.txt").write_text("nothing here")
        reg = _reg()
        res = reg.get("fs_search").invoke(
            {"query": "XYZNOTFOUND"}, _ctx(tmp_path)
        )
        assert res.ok
        assert len(res.output) == 0

    def test_search_missing_query(self, tmp_path):
        reg = _reg()
        res = reg.get("fs_search").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_search_glob_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("target_text")
        (tmp_path / "b.txt").write_text("target_text")
        reg = _reg()
        res = reg.get("fs_search").invoke(
            {"query": "target_text", "pattern": "*.py"}, _ctx(tmp_path)
        )
        assert res.ok
        assert all(r["file"].endswith(".py") for r in res.output)
