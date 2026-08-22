"""Memory store interface.

A store persists :class:`MemoryRecord`s and retrieves them by semantic
similarity within a scope. Backends: :class:`LocalMemoryStore` (SQLite +
in-process vectors) and a Supabase/pgvector store. The orchestrator depends
only on this interface.
"""
from __future__ import annotations

import abc
from typing import Optional

from shared.contracts import MemoryRecord, MemoryResult, MemoryScope


class MemoryStore(abc.ABC):
    @abc.abstractmethod
    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Persist a record (computing its embedding if absent)."""

    @abc.abstractmethod
    def search(
        self,
        query: str,
        *,
        scope: Optional[MemoryScope] = None,
        project: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemoryResult]:
        """Return the most similar records, highest score first."""

    @abc.abstractmethod
    def list(
        self,
        *,
        scope: Optional[MemoryScope] = None,
        project: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        """Return recent records (no similarity ranking)."""

    def close(self) -> None:  # optional override
        pass
