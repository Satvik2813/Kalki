"""Supabase / pgvector memory backend.

Implements the same :class:`MemoryStore` interface as the local backend, using
Postgres + the pgvector extension for scalable semantic search. Requires
``psycopg`` (``pip install 'kalki[supabase]'``) and ``SUPABASE_DB_URL``.

This backend is import-guarded and only instantiated when
``KALKI_MEMORY_BACKEND=supabase``; the core never imports it directly. The DDL
below is idempotent so first run provisions the table + index.
"""
from __future__ import annotations

from typing import Optional

from memory.base import MemoryStore
from memory.embeddings import embed
from shared.contracts import MemoryRecord, MemoryResult, MemoryScope

_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS kalki_memories (
    id          TEXT PRIMARY KEY,
    scope       TEXT NOT NULL,
    content     TEXT NOT NULL,
    project     TEXT,
    session_id  TEXT,
    tags        JSONB NOT NULL DEFAULT '[]',
    metadata    JSONB NOT NULL DEFAULT '{}',
    embedding   VECTOR(%(dim)s),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kalki_mem_scope   ON kalki_memories(scope);
CREATE INDEX IF NOT EXISTS idx_kalki_mem_project ON kalki_memories(project);
"""


class SupabaseMemoryStore(MemoryStore):
    def __init__(self, db_url: str, embedding_dim: int = 384):
        if not db_url:
            raise ValueError("SUPABASE_DB_URL is required for the supabase backend.")
        try:
            import psycopg  # type: ignore
        except ImportError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "psycopg not installed. Run: pip install 'kalki[supabase]'"
            ) from exc
        self._psycopg = psycopg
        self.embedding_dim = embedding_dim
        self._conn = psycopg.connect(db_url, autocommit=True)
        with self._conn.cursor() as cur:
            cur.execute(_DDL % {"dim": embedding_dim})

    @staticmethod
    def _vec_literal(values: list[float]) -> str:
        return "[" + ",".join(f"{v:.6f}" for v in values) + "]"

    def add(self, record: MemoryRecord) -> MemoryRecord:
        import json
        if record.embedding is None:
            record.embedding = embed(record.content, self.embedding_dim)
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO kalki_memories
                   (id, scope, content, project, session_id, tags, metadata,
                    embedding, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now())
                   ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content""",
                (record.id, record.scope.value, record.content, record.project,
                 record.session_id, json.dumps(record.tags),
                 json.dumps(record.metadata), self._vec_literal(record.embedding)),
            )
        return record

    def search(self, query, *, scope=None, project=None, session_id=None,
               limit=5, min_score=0.0):
        qv = self._vec_literal(embed(query, self.embedding_dim))
        clauses, params = [], []
        if scope is not None:
            clauses.append("scope = %s")
            params.append(scope.value if isinstance(scope, MemoryScope) else scope)
        if project is not None:
            clauses.append("project = %s")
            params.append(project)
        if session_id is not None:
            clauses.append("session_id = %s")
            params.append(session_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # cosine distance operator <=> ; similarity = 1 - distance
        sql = (
            f"SELECT id, scope, content, project, session_id, tags, metadata, "
            f"created_at, 1 - (embedding <=> %s) AS score "
            f"FROM kalki_memories {where} ORDER BY embedding <=> %s LIMIT %s"
        )
        args = [qv] + params + [qv, limit]
        import json
        out: list[MemoryResult] = []
        with self._conn.cursor() as cur:
            cur.execute(sql, args)
            for row in cur.fetchall():
                score = float(row[8])
                if score < min_score:
                    continue
                rec = MemoryRecord(
                    id=row[0], scope=MemoryScope(row[1]), content=row[2],
                    project=row[3], session_id=row[4],
                    tags=row[5] if isinstance(row[5], list) else json.loads(row[5] or "[]"),
                    metadata=row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}"),
                    created_at=str(row[7]),
                )
                out.append(MemoryResult(record=rec, score=round(score, 4)))
        return out

    def list(self, *, scope=None, project=None, session_id=None, limit=100):
        results = self.search("", scope=scope, project=project,
                              session_id=session_id, limit=limit)
        return [r.record for r in results]

    def close(self) -> None:
        self._conn.close()
