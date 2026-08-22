"""Local SQLite memory store with in-process vector search.

Zero-config, offline default backend. Stores every scope (session / project /
long-term) in one table and ranks retrieval by cosine similarity over the
hashed embeddings. Suitable for a hackathon-scale corpus; the Supabase backend
implements the same interface with pgvector for scale.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Optional

from memory.base import MemoryStore
from memory.embeddings import cosine, embed
from shared.contracts import MemoryRecord, MemoryResult, MemoryScope

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          TEXT PRIMARY KEY,
    scope       TEXT NOT NULL,
    content     TEXT NOT NULL,
    project     TEXT,
    session_id  TEXT,
    tags        TEXT NOT NULL DEFAULT '[]',
    metadata    TEXT NOT NULL DEFAULT '{}',
    embedding   TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mem_scope   ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_mem_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_mem_session ON memories(session_id);
"""


class LocalMemoryStore(MemoryStore):
    def __init__(self, db_path: str = "kalki_local.sqlite3", embedding_dim: int = 384):
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    # -- writes --------------------------------------------------
    def add(self, record: MemoryRecord) -> MemoryRecord:
        if record.embedding is None:
            record.embedding = embed(record.content, self.embedding_dim)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO memories
                   (id, scope, content, project, session_id, tags, metadata,
                    embedding, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    record.id,
                    record.scope.value,
                    record.content,
                    record.project,
                    record.session_id,
                    json.dumps(record.tags),
                    json.dumps(record.metadata),
                    json.dumps(record.embedding),
                    record.created_at,
                ),
            )
        return record

    # -- reads ---------------------------------------------------
    def _rows(self, scope, project, session_id, limit):
        clauses, params = [], []
        if scope is not None:
            clauses.append("scope = ?")
            params.append(scope.value if isinstance(scope, MemoryScope) else scope)
        if project is not None:
            clauses.append("project = ?")
            params.append(project)
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM memories {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    @staticmethod
    def _to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            scope=MemoryScope(row["scope"]),
            content=row["content"],
            project=row["project"],
            session_id=row["session_id"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            embedding=json.loads(row["embedding"]),
            created_at=row["created_at"],
        )

    def list(self, *, scope=None, project=None, session_id=None, limit=100):
        rows = self._rows(scope, project, session_id, limit)
        return [self._to_record(r) for r in rows]

    def search(self, query, *, scope=None, project=None, session_id=None,
               limit=5, min_score=0.0):
        qv = embed(query, self.embedding_dim)
        # Pull a candidate window (scope/project filtered) then rank in-process.
        rows = self._rows(scope, project, session_id, limit=1000)
        scored: list[MemoryResult] = []
        for r in rows:
            rec = self._to_record(r)
            score = cosine(qv, rec.embedding or [])
            if score >= min_score:
                scored.append(MemoryResult(record=rec, score=round(score, 4)))
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:limit]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
