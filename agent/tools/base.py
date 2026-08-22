"""Tool contract and registry.

A tool is any object exposing a :class:`ToolSpec` and a ``run(args, ctx)``
method returning a :class:`ToolResult`. Tools should never raise for expected
failures — they return ``ToolResult.failure(...)`` with a classified
:class:`FailureClass` so the recovery engine can reason about them.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec


@dataclass
class ToolContext:
    """Ambient services/config a tool may use during execution."""

    workspace_root: str = "."
    run_id: str = ""
    project: Optional[str] = None
    scratch: dict[str, Any] = field(default_factory=dict)


class Tool(abc.ABC):
    spec: ToolSpec

    @abc.abstractmethod
    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        ...

    # -- helper so subclasses get timing + exception safety for free ----
    def invoke(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        start = time.perf_counter()
        try:
            result = self.run(args or {}, ctx)
        except Exception as exc:  # unexpected -> classified failure, never crash
            result = ToolResult.failure(
                self.spec.name, f"{type(exc).__name__}: {exc}",
                failure_class=FailureClass.TOOL_ERROR,
            )
        result.duration_ms = int((time.perf_counter() - start) * 1000)
        return result


class FunctionTool(Tool):
    """Adapt a plain function into a Tool (convenience for Dev 3)."""

    def __init__(self, spec: ToolSpec,
                 fn: Callable[[dict[str, Any], ToolContext], ToolResult]):
        self.spec = spec
        self._fn = fn

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return self._fn(args, ctx)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def register_function(self, spec: ToolSpec, fn) -> None:
        self.register(FunctionTool(spec, fn))

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def risk_of(self, name: str) -> RiskLevel:
        tool = self._tools.get(name)
        return tool.spec.risk if tool else RiskLevel.SAFE
