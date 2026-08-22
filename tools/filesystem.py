"""Filesystem tools — comprehensive file operations for KALKI.

Provides: ``fs_read``, ``fs_write``, ``fs_edit``, ``fs_list``, ``fs_search``.

All operations are sandboxed to ``ctx.workspace_root``.  Path traversal
attempts return ``FailureClass.PERMISSION``.  Encoding is preserved where
possible (default UTF-8).
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec


# ── helpers ──────────────────────────────────────────────────────
def _sandbox(ctx: ToolContext, rel: str) -> Path:
    """Resolve *rel* inside the workspace sandbox.  Raises on escape."""
    root = Path(ctx.workspace_root).resolve()
    target = (root / rel).resolve()
    if root != target and root not in target.parents:
        raise PermissionError(f"path {rel!r} escapes workspace sandbox")
    return target


def _perm_failure(tool: str, msg: str) -> ToolResult:
    return ToolResult.failure(tool, msg, FailureClass.PERMISSION)


def _arg_error(tool: str, msg: str) -> ToolResult:
    return ToolResult.failure(tool, msg, FailureClass.TOOL_ERROR)


# ── fs_read ──────────────────────────────────────────────────────
class FsReadTool(Tool):
    spec = ToolSpec(
        name="fs_read",
        description=(
            "Read a text file within the workspace.  Supports optional "
            "line-range selection (start_line / end_line, 1-indexed)."
        ),
        parameters={
            "path": "str — relative path inside workspace",
            "start_line": "int (optional, 1-indexed) — first line to return",
            "end_line": "int (optional, 1-indexed) — last line to return",
            "encoding": "str (optional, default 'utf-8')",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not path:
            return _arg_error(self.spec.name, "missing 'path'")
        try:
            target = _sandbox(ctx, path)
        except PermissionError as e:
            return _perm_failure(self.spec.name, str(e))
        if not target.is_file():
            return _arg_error(self.spec.name, f"not found: {path}")

        encoding = args.get("encoding", "utf-8")
        try:
            text = target.read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError) as e:
            return _arg_error(self.spec.name, f"encoding error: {e}")

        start = args.get("start_line")
        end = args.get("end_line")
        if start is not None or end is not None:
            lines = text.splitlines(keepends=True)
            s = max(0, (int(start) - 1)) if start else 0
            e = int(end) if end else len(lines)
            text = "".join(lines[s:e])

        return ToolResult.success(
            self.spec.name,
            output=text,
            total_lines=text.count("\n") + (1 if text and not text.endswith("\n") else 0),
            file_size=target.stat().st_size,
        )


# ── fs_write ─────────────────────────────────────────────────────
class FsWriteTool(Tool):
    spec = ToolSpec(
        name="fs_write",
        description="Create or overwrite a text file within the workspace.",
        parameters={
            "path": "str — relative path",
            "content": "str — file content",
            "encoding": "str (optional, default 'utf-8')",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not path:
            return _arg_error(self.spec.name, "missing 'path'")
        content = args.get("content", "")
        try:
            target = _sandbox(ctx, path)
        except PermissionError as e:
            return _perm_failure(self.spec.name, str(e))

        encoding = args.get("encoding", "utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return ToolResult.success(
            self.spec.name,
            output=f"wrote {len(content)} bytes to {path}",
            code_changed=True,
        )


# ── fs_edit ──────────────────────────────────────────────────────
class FsEditTool(Tool):
    spec = ToolSpec(
        name="fs_edit",
        description=(
            "Surgically edit a file: replace exact text matches or replace a "
            "line range.  Returns the updated file content."
        ),
        parameters={
            "path": "str — relative path",
            "old_text": "str (optional) — exact text to find and replace",
            "new_text": "str — replacement text",
            "start_line": "int (optional, 1-indexed) — first line of range to replace",
            "end_line": "int (optional, 1-indexed) — last line of range to replace",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = args.get("path")
        if not path:
            return _arg_error(self.spec.name, "missing 'path'")
        try:
            target = _sandbox(ctx, path)
        except PermissionError as e:
            return _perm_failure(self.spec.name, str(e))
        if not target.is_file():
            return _arg_error(self.spec.name, f"not found: {path}")

        text = target.read_text(encoding="utf-8")
        old_text = args.get("old_text")
        new_text = args.get("new_text", "")

        if old_text is not None:
            if old_text not in text:
                return _arg_error(
                    self.spec.name, "old_text not found in file"
                )
            text = text.replace(old_text, new_text)
        elif args.get("start_line") is not None:
            lines = text.splitlines(keepends=True)
            s = max(0, int(args["start_line"]) - 1)
            e = int(args.get("end_line", s + 1))
            lines[s:e] = [new_text if new_text.endswith("\n") else new_text + "\n"]
            text = "".join(lines)
        else:
            return _arg_error(
                self.spec.name, "must provide 'old_text' or 'start_line'"
            )

        target.write_text(text, encoding="utf-8")
        return ToolResult.success(
            self.spec.name,
            output=f"edited {path}",
            code_changed=True,
        )


# ── fs_list ──────────────────────────────────────────────────────
class FsListTool(Tool):
    spec = ToolSpec(
        name="fs_list",
        description=(
            "List files and directories within the workspace.  Supports "
            "recursive listing and glob pattern filtering."
        ),
        parameters={
            "path": "str (optional, default '.') — relative directory",
            "recursive": "bool (optional, default false)",
            "pattern": "str (optional) — glob pattern to filter (e.g. '*.py')",
            "max_entries": "int (optional, default 500)",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        rel = args.get("path", ".")
        try:
            target = _sandbox(ctx, rel)
        except PermissionError as e:
            return _perm_failure(self.spec.name, str(e))
        if not target.is_dir():
            return _arg_error(self.spec.name, f"not a directory: {rel}")

        recursive = bool(args.get("recursive", False))
        pattern = args.get("pattern")
        max_entries = int(args.get("max_entries", 500))

        root = Path(ctx.workspace_root).resolve()
        entries: list[dict[str, Any]] = []

        if recursive:
            iterator = target.rglob("*")
        else:
            iterator = target.iterdir()

        for p in sorted(iterator):
            # Skip hidden dirs like .git
            rel_path = str(p.relative_to(root)).replace("\\", "/")
            if pattern and not fnmatch.fnmatch(p.name, pattern):
                continue
            entries.append({
                "path": rel_path,
                "type": "dir" if p.is_dir() else "file",
                "size": p.stat().st_size if p.is_file() else None,
            })
            if len(entries) >= max_entries:
                break

        return ToolResult.success(
            self.spec.name,
            output=entries,
            total=len(entries),
            truncated=len(entries) >= max_entries,
        )


# ── fs_search ────────────────────────────────────────────────────
class FsSearchTool(Tool):
    spec = ToolSpec(
        name="fs_search",
        description=(
            "Search file contents (grep-like).  Returns matching lines with "
            "file paths and line numbers."
        ),
        parameters={
            "query": "str — text or regex pattern to search",
            "path": "str (optional, default '.') — directory to search in",
            "pattern": "str (optional) — glob filter for filenames (e.g. '*.py')",
            "is_regex": "bool (optional, default false)",
            "max_results": "int (optional, default 100)",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = args.get("query")
        if not query:
            return _arg_error(self.spec.name, "missing 'query'")
        rel = args.get("path", ".")
        try:
            target = _sandbox(ctx, rel)
        except PermissionError as e:
            return _perm_failure(self.spec.name, str(e))
        if not target.is_dir():
            return _arg_error(self.spec.name, f"not a directory: {rel}")

        file_pattern = args.get("pattern", "*")
        is_regex = bool(args.get("is_regex", False))
        max_results = int(args.get("max_results", 100))

        if is_regex:
            try:
                regex = re.compile(query)
            except re.error as e:
                return _arg_error(self.spec.name, f"invalid regex: {e}")
        else:
            regex = None

        root = Path(ctx.workspace_root).resolve()
        results: list[dict[str, Any]] = []

        for filepath in sorted(target.rglob(file_pattern)):
            if not filepath.is_file():
                continue
            # Skip binary files
            try:
                content = filepath.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, PermissionError):
                continue

            for lineno, line in enumerate(content.splitlines(), start=1):
                matched = regex.search(line) if regex else (query in line)
                if matched:
                    rel_path = str(filepath.relative_to(root)).replace("\\", "/")
                    results.append({
                        "file": rel_path,
                        "line": lineno,
                        "content": line.rstrip(),
                    })
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break

        return ToolResult.success(
            self.spec.name,
            output=results,
            total=len(results),
            truncated=len(results) >= max_results,
        )


# ── registration ─────────────────────────────────────────────────
def register_filesystem_tools(registry: ToolRegistry) -> None:
    for cls in (FsReadTool, FsWriteTool, FsEditTool, FsListTool, FsSearchTool):
        registry.register(cls())
