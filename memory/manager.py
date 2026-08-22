"""High-level memory operations used by the orchestrator.

Wraps a :class:`MemoryStore` with the three memory layers KALKI must satisfy:

  * **session**   — objective, plan, tool calls, errors for the current run
  * **project**   — durable knowledge about a repository
  * **long-term** — engineering experience (incidents, bugs, successful fixes)
                    that vector-retrieval surfaces to influence future plans

The manager also implements the retrieval path that makes memory *influence
decisions*: :meth:`recall_experience` finds similar past incidents so the
planner/recovery engine can reuse what worked before.
"""
from __future__ import annotations

from typing import Optional

from config.settings import Settings, get_settings
from memory.base import MemoryStore
from memory.local_store import LocalMemoryStore
from shared.contracts import MemoryRecord, MemoryResult, MemoryScope


def build_memory(settings: Optional[Settings] = None) -> MemoryStore:
    """Factory: pick a backend from settings, always returning a usable store."""
    settings = settings or get_settings()
    if settings.memory_backend == "supabase":
        try:
            from memory.supabase_store import SupabaseMemoryStore
            return SupabaseMemoryStore(settings.supabase_db_url, settings.embedding_dim)
        except Exception as exc:  # fall back to local rather than crash the agent
            import logging
            logging.getLogger("kalki.memory").warning(
                "Supabase backend unavailable (%s); using local store.", exc
            )
    return LocalMemoryStore(settings.local_db_path, settings.embedding_dim)


class MemoryManager:
    def __init__(self, store: Optional[MemoryStore] = None,
                 settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.store = store or build_memory(self.settings)

    # -- session layer -------------------------------------------
    def record_session(self, session_id: str, content: str,
                        tags: Optional[list[str]] = None, **metadata) -> MemoryRecord:
        return self.store.add(MemoryRecord(
            scope=MemoryScope.SESSION, content=content, session_id=session_id,
            tags=tags or [], metadata=metadata,
        ))

    # -- project layer -------------------------------------------
    def record_project(self, project: str, content: str,
                       tags: Optional[list[str]] = None, **metadata) -> MemoryRecord:
        return self.store.add(MemoryRecord(
            scope=MemoryScope.PROJECT, content=content, project=project,
            tags=tags or [], metadata=metadata,
        ))

    # -- long-term layer -----------------------------------------
    def record_experience(self, content: str, project: Optional[str] = None,
                          tags: Optional[list[str]] = None, **metadata) -> MemoryRecord:
        """Store a durable engineering lesson: an incident, bug, or the fix
        that resolved it — the corpus long-term retrieval draws on."""
        return self.store.add(MemoryRecord(
            scope=MemoryScope.LONG_TERM, content=content, project=project,
            tags=tags or [], metadata=metadata,
        ))

    # -- retrieval that influences decisions ---------------------
    def recall_experience(self, query: str, project: Optional[str] = None,
                          limit: int = 3, min_score: float = 0.05) -> list[MemoryResult]:
        """Find similar past incidents/fixes to inform the current plan."""
        return self.store.search(
            query, scope=MemoryScope.LONG_TERM, limit=limit, min_score=min_score,
        )

    def recall_project(self, project: str, query: str,
                       limit: int = 3) -> list[MemoryResult]:
        return self.store.search(
            query, scope=MemoryScope.PROJECT, project=project, limit=limit,
        )

    def session_trace(self, session_id: str, limit: int = 200) -> list[MemoryRecord]:
        return self.store.list(scope=MemoryScope.SESSION, session_id=session_id,
                               limit=limit)

    def close(self) -> None:
        self.store.close()
