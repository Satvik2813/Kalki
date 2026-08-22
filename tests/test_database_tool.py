"""Tests for database tools (db_query, db_execute, db_schema)."""
import sqlite3
from pathlib import Path

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass
from tools.database_tool import register_database_tools


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_database_tools(r)
    return r


def _ctx_with_db(tmp_path) -> ToolContext:
    """Create a workspace with a SQLite database containing test data."""
    db_path = tmp_path / "kalki.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@test.com')")
    conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@test.com')")
    conn.commit()
    conn.close()
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


class TestDbQuery:
    def test_select(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke(
            {"sql": "SELECT * FROM users"}, ctx
        )
        assert res.ok
        assert res.output["row_count"] == 2
        assert res.output["columns"] == ["id", "name", "email"]

    def test_select_with_params(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke(
            {"sql": "SELECT * FROM users WHERE name = ?", "params": ["Alice"]}, ctx
        )
        assert res.ok
        assert res.output["row_count"] == 1
        assert res.output["rows"][0]["name"] == "Alice"

    def test_blocks_write_via_query(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke(
            {"sql": "DELETE FROM users WHERE id = 1"}, ctx
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_blocks_insert_via_query(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke(
            {"sql": "INSERT INTO users VALUES (3, 'Eve', 'eve@test.com')"}, ctx
        )
        assert not res.ok
        assert res.failure_class == FailureClass.PERMISSION

    def test_missing_sql(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke({}, ctx)
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_bad_sql(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke(
            {"sql": "SELECT * FROM nonexistent_table"}, ctx
        )
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_max_rows(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_query").invoke(
            {"sql": "SELECT * FROM users", "max_rows": 1}, ctx
        )
        assert res.ok
        assert res.output["row_count"] == 1
        assert res.output["truncated"] is True


class TestDbExecute:
    def test_insert(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_execute").invoke(
            {"sql": "INSERT INTO users VALUES (3, 'Charlie', 'c@test.com')"}, ctx
        )
        assert res.ok
        assert res.output["affected_rows"] == 1

    def test_delete(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_execute").invoke(
            {"sql": "DELETE FROM users WHERE id = 1"}, ctx
        )
        assert res.ok
        assert res.output["affected_rows"] == 1

    def test_missing_sql(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_execute").invoke({}, ctx)
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_risk_level_is_dangerous(self):
        reg = _reg()
        tool = reg.get("db_execute")
        assert tool.spec.risk == RiskLevel.DANGEROUS


class TestDbSchema:
    def test_list_tables(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_schema").invoke({}, ctx)
        assert res.ok
        assert "users" in res.output["tables"]

    def test_inspect_table(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_schema").invoke({"table": "users"}, ctx)
        assert res.ok
        cols = [c["name"] for c in res.output["columns"]]
        assert "id" in cols
        assert "name" in cols
        assert "email" in cols

    def test_nonexistent_table(self, tmp_path):
        ctx = _ctx_with_db(tmp_path)
        reg = _reg()
        res = reg.get("db_schema").invoke({"table": "nope"}, ctx)
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR


from shared.contracts import RiskLevel
