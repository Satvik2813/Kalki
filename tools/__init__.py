"""KALKI Dev 3 — Tool implementations.

Provides production-quality tools for filesystem, terminal, git, web,
database access and registers them into the core ToolRegistry.

Usage:
    from tools import register_all_tools
    register_all_tools(registry)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.tools.base import ToolRegistry


def register_all_tools(registry: "ToolRegistry") -> "ToolRegistry":
    """Register all Dev 3 tools into Satvik's existing registry.

    Call this *after* ``register_builtins()`` so Dev 3 implementations
    augment (or replace) the minimal built-ins.
    """
    from tools.filesystem import register_filesystem_tools
    from tools.terminal import register_terminal_tools
    from tools.git_tool import register_git_tools
    from tools.web_tool import register_web_tools
    from tools.database_tool import register_database_tools
    from integrations.github_tool import register_github_tools
    from integrations.vercel_tool import register_vercel_tools
    from sandbox.docker_sandbox import register_sandbox_tools

    register_filesystem_tools(registry)
    register_terminal_tools(registry)
    register_git_tools(registry)
    register_web_tools(registry)
    register_database_tools(registry)
    register_github_tools(registry)
    register_vercel_tools(registry)
    register_sandbox_tools(registry)

    return registry
