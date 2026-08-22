"""Shared, dependency-free contracts and utilities for KALKI.

Everything in :mod:`shared.contracts` is a stable integration surface:
Dev 2 (frontend/API consumers) and Dev 3 (tool authors) build against
these types and never need to modify the core to integrate.
"""
from shared.contracts import (
    AgentEvent,
    AgentState,
    EventType,
    ExecutionResult,
    ExecutionStatus,
    FailureClass,
    MemoryRecord,
    MemoryResult,
    MemoryScope,
    Plan,
    RiskLevel,
    Task,
    TaskStatus,
    ToolResult,
    ToolSpec,
    new_id,
    utcnow_iso,
)

__all__ = [
    "AgentEvent",
    "AgentState",
    "EventType",
    "ExecutionResult",
    "ExecutionStatus",
    "FailureClass",
    "MemoryRecord",
    "MemoryResult",
    "MemoryScope",
    "Plan",
    "RiskLevel",
    "Task",
    "TaskStatus",
    "ToolResult",
    "ToolSpec",
    "new_id",
    "utcnow_iso",
]
