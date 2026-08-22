"""Tool interface, registry, and built-in reference tools.

Dev 3 authors tools against :class:`Tool` / :class:`ToolContext` and registers
them in a :class:`ToolRegistry`; the core never needs modification to add a
tool. The built-ins here are minimal reference implementations so the engine
has a working toolbelt out of the box.
"""
from agent.tools.base import Tool, ToolContext, ToolRegistry
from agent.tools.builtins import register_builtins

__all__ = ["Tool", "ToolContext", "ToolRegistry", "register_builtins"]
