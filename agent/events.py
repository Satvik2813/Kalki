"""Event bus for observable execution.

The orchestrator emits :class:`AgentEvent`s through an :class:`EventBus`. The
bus is synchronous-callback based (works everywhere, no event loop needed) and
also buffers events per run so late subscribers — e.g. an SSE stream that
connects after a run starts, or the API polling ``GET /events`` — can replay
history. Dev 2's dashboard subscribes to these.
"""
from __future__ import annotations

import threading
from typing import Callable

from shared.contracts import AgentEvent, EventType

Subscriber = Callable[[AgentEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []
        self._history: list[AgentEvent] = []
        self._seq = 0
        self._lock = threading.Lock()

    def subscribe(self, fn: Subscriber) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(fn)

        def unsubscribe() -> None:
            with self._lock:
                if fn in self._subscribers:
                    self._subscribers.remove(fn)

        return unsubscribe

    def emit(self, event: AgentEvent) -> AgentEvent:
        with self._lock:
            self._seq += 1
            event.seq = self._seq
            self._history.append(event)
            subs = list(self._subscribers)
        for fn in subs:
            try:
                fn(event)
            except Exception:  # a bad subscriber must not break execution
                pass
        return event

    def publish(self, type_: EventType, run_id: str, message: str = "",
                **data) -> AgentEvent:
        return self.emit(AgentEvent(type=type_, task_id=run_id,
                                    message=message, data=data))

    def history(self, after_seq: int = 0) -> list[AgentEvent]:
        with self._lock:
            return [e for e in self._history if e.seq > after_seq]
