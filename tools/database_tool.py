"""Database access tool for KALKI.

Provides: ``db_query`` (SAFE — read-only), ``db_execute`` (DANGEROUS —
write ops), ``db_schema`` (SAFE — inspect tables).

Uses stdlib ``sqlite3`` by default.  Connection string from
``KALKI_DB_URL`` env var or falls back to an in-workspace SQLite file.
Write operations require approval (DANGEROUS risk level).
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec

# SQL statements that are considered write operations.
_WRITE_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)


def _get_connection(ctx: ToolContext) -> sqlite3.Connection:
    """Open a SQLite connection.  Prefers KALKI_DB_URL env, then
    workspace-local ``kalki.sqlite3``."""
    db_url = os.environ.get("KALKI_DB_URL", "")
    if db_url:
        return sqlite3.connect(db_url)
    db_path = Path(ctx.workspace_root) / "kalki.sqlite3"
    return sqlite3.connect(str(db_path))


# ── db_query ─────────────────────────────────────────────────────
class DbQueryTool(Tool):
    spec = ToolSpec(
        name="db_query",
        description="Execute a read-only SQL query and return results.",
        parameters={
            "sql": "str — SELECT query",
            "params": "list (optional) — query parameters for safe binding",
            "max_rows": "int (optional, default 100) — limit rows returned",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        sql = args.get("sql", "").strip()
        if not sql:
            return ToolResult.failure(
                self.spec.name, "missing 'sql'", FailureClass.TOOL_ERROR
            )

        # Block write operations through the read-only tool.
        if _WRITE_PATTERN.match(sql):
            return ToolResult.failure(
                self.spec.name,
                "write operations not allowed via db_query — use db_execute",
                FailureClass.PERMISSION,
            )

        params = args.get("params", [])
        max_rows = int(args.get("max_rows", 100))

        try:
            conn = _get_connection(ctx)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [dict(row) for row in cursor.fetchmany(max_rows)]
            conn.close()
        except sqlite3.Error as e:
            return ToolResult.failure(
                self.spec.name, f"SQL error: {e}",
                FailureClass.TOOL_ERROR,
            )

        return ToolResult.success(self.spec.name, output={
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(rows) >= max_rows,
        })


# ── db_execute ───────────────────────────────────────────────────
class DbExecuteTool(Tool):
    spec = ToolSpec(
        name="db_execute",
        description=(
            "Execute a write SQL statement (INSERT, UPDATE, DELETE, etc.).  "
            "Requires human approval (DANGEROUS risk)."
        ),
        parameters={
            "sql": "str — SQL statement",
            "params": "list (optional) — query parameters for safe binding",
        },
        risk=RiskLevel.DANGEROUS,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        sql = args.get("sql", "").strip()
        if not sql:
            return ToolResult.failure(
                self.spec.name, "missing 'sql'", FailureClass.TOOL_ERROR
            )

        params = args.get("params", [])

        try:
            conn = _get_connection(ctx)
            cursor = conn.execute(sql, params)
            conn.commit()
            affected = cursor.rowcount
            conn.close()
        except sqlite3.Error as e:
            return ToolResult.failure(
                self.spec.name, f"SQL error: {e}",
                FailureClass.TOOL_ERROR,
            )

        return ToolResult.success(self.spec.name, output={
            "affected_rows": affected,
            "sql": sql,
        })


# ── db_schema ────────────────────────────────────────────────────
class DbSchemaTool(Tool):
    spec = ToolSpec(
        name="db_schema",
        description="Inspect database table schemas.",
        parameters={
            "table": "str (optional) — specific table, or omit to list all tables",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        try:
            conn = _get_connection(ctx)
            table = args.get("table")

            if table:
                cursor = conn.execute(f"PRAGMA table_info('{table}')")
                columns = [
                    {"name": r[1], "type": r[2], "notnull": bool(r[3]),
                     "default": r[4], "pk": bool(r[5])}
                    for r in cursor.fetchall()
                ]
                conn.close()
                if not columns:
                    return ToolResult.failure(
                        self.spec.name, f"table '{table}' not found",
                        FailureClass.TOOL_ERROR,
                    )
                return ToolResult.success(self.spec.name, output={
                    "table": table, "columns": columns,
                })
            else:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [r[0] for r in cursor.fetchall()]
                conn.close()
                return ToolResult.success(self.spec.name, output={
                    "tables": tables,
                })
        except sqlite3.Error as e:
            return ToolResult.failure(
                self.spec.name, f"database error: {e}",
                FailureClass.TOOL_ERROR,
            )


# ── registration ─────────────────────────────────────────────────
def register_database_tools(registry: ToolRegistry) -> None:
    for cls in (DbQueryTool, DbExecuteTool, DbSchemaTool):
        registry.register(cls())
