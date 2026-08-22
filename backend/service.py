"""Run lifecycle service.

Owns a shared model provider, memory manager and tool registry, and manages
individual runs — each with its own :class:`Orchestrator`, event bus and
permission manager. Long-term memory is shared across runs so engineering
experience accumulates. Runs execute on a background thread so events can be
streamed while a run is in flight.

This is the seam the API layer sits on; it has no web dependency and is fully
unit-testable on its own.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from agent.events import EventBus
from agent.orchestrator import Orchestrator
from agent.permissions import PermissionManager
from agent.tools.base import ToolRegistry
from agent.tools.builtins import register_builtins
from config.settings import Settings, get_settings
from memory.manager import MemoryManager
from models.registry import get_provider
from shared.contracts import AgentEvent, AgentState, ExecutionStatus


@dataclass
class RunHandle:
    state: AgentState
    orchestrator: Orchestrator
    events: EventBus
    thread: Optional[threading.Thread] = None
    result: dict = field(default_factory=dict)

    @property
    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


class KalkiService:
    def __init__(self, settings: Optional[Settings] = None,
                 registry: Optional[ToolRegistry] = None):
        self.settings = settings or get_settings()
        self.provider = get_provider(settings=self.settings)
        self.memory = MemoryManager(settings=self.settings)
        self.registry = registry or register_builtins(ToolRegistry())
        self._runs: dict[str, RunHandle] = {}
        self._lock = threading.Lock()

    # ── lifecycle ───────────────────────────────────────────────
    def create(self, objective: str, project: Optional[str] = None,
               autonomy: Optional[str] = None) -> AgentState:
        bus = EventBus()
        perms = PermissionManager(autonomy=autonomy or self.settings.autonomy)
        orch = Orchestrator(
            provider=self.provider, memory=self.memory, registry=self.registry,
            settings=self.settings, event_bus=bus, permissions=perms,
        )
        state = AgentState(objective=objective, project=project)
        handle = RunHandle(state=state, orchestrator=orch, events=bus)
        with self._lock:
            self._runs[state.id] = handle
        return state

    def _drive(self, handle: RunHandle, approvals: Optional[list[str]] = None) -> None:
        state, result = handle.orchestrator.resume(handle.state, approvals=approvals)
        handle.state = state
        handle.result = result.to_dict()

    def start(self, run_id: str, block: bool = False) -> AgentState:
        handle = self._require(run_id)
        if block:
            self._drive(handle)
            return handle.state
        t = threading.Thread(target=self._drive, args=(handle,), daemon=True)
        handle.thread = t
        t.start()
        return handle.state

    def approve(self, run_id: str, tools: list[str], block: bool = False) -> AgentState:
        handle = self._require(run_id)
        if block:
            self._drive(handle, approvals=tools)
            return handle.state
        t = threading.Thread(target=self._drive, args=(handle, tools), daemon=True)
        handle.thread = t
        t.start()
        return handle.state

    # ── queries ─────────────────────────────────────────────────
    def get(self, run_id: str) -> AgentState:
        return self._require(run_id).state

    def result(self, run_id: str) -> dict:
        return self._require(run_id).result

    def events(self, run_id: str, after_seq: int = 0) -> list[AgentEvent]:
        return self._require(run_id).events.history(after_seq=after_seq)

    def subscribe(self, run_id: str, fn):
        return self._require(run_id).events.subscribe(fn)

    def list_runs(self) -> list[AgentState]:
        with self._lock:
            return [h.state for h in self._runs.values()]

    def status(self, run_id: str) -> ExecutionStatus:
        return self._require(run_id).state.status

    # ── memory passthrough (for GET /api/memory, /api/projects) ──
    def recent_memories(self, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in self.memory.store.list(limit=limit)]

    def projects(self) -> list[str]:
        seen = {r.project for r in self.memory.store.list(limit=1000) if r.project}
        return sorted(seen)

    # ── internal ────────────────────────────────────────────────
    def _require(self, run_id: str) -> RunHandle:
        with self._lock:
            handle = self._runs.get(run_id)
        if handle is None:
            raise KeyError(f"unknown run {run_id!r}")
        return handle
