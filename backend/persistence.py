"""Run and event persistence layer."""
from __future__ import annotations

import json
from typing import Optional

from config.settings import Settings
from shared.contracts import AgentState, AgentEvent

class RunStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._conn = None
        if self.settings.memory_backend == "supabase" and self.settings.supabase_db_url:
            try:
                import psycopg  # type: ignore
                self._conn = psycopg.connect(self.settings.supabase_db_url, autocommit=True)
            except Exception as e:
                import logging
                logging.getLogger("kalki.persistence").warning("RunStore DB connection failed: %s", e)
                
    def save_state(self, state: AgentState) -> None:
        if not self._conn or not state.user_id:
            return
        try:
            with self._conn.cursor() as cur:
                if state.project:
                    cur.execute(
                        "INSERT INTO projects (id, user_id, name) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                        (state.project, state.user_id, state.project)
                    )
                cur.execute(
                    """INSERT INTO agent_runs
                       (id, user_id, project_id, objective, status, node, plan, current_task_id, plan_revisions, error, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                       ON CONFLICT (id) DO UPDATE SET
                       status=EXCLUDED.status, node=EXCLUDED.node, plan=EXCLUDED.plan,
                       current_task_id=EXCLUDED.current_task_id, plan_revisions=EXCLUDED.plan_revisions,
                       error=EXCLUDED.error, updated_at=now()""",
                    (state.id, state.user_id, state.project, state.objective, state.status.value,
                     state.node, json.dumps(state.plan.to_dict()) if state.plan else None,
                     state.current_task_id, state.plan_revisions, state.error)
                )
        except Exception as e:
            import logging
            logging.getLogger("kalki.persistence").error("Failed to save state: %s", e)

    def save_event(self, event: AgentEvent) -> None:
        if not self._conn or not event.user_id:
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO agent_events (id, run_id, user_id, type, seq, message, data)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO NOTHING""",
                    (event.id, event.task_id, event.user_id, event.type.value, event.seq,
                     event.message, json.dumps(event.data))
                )
        except Exception as e:
            import logging
            logging.getLogger("kalki.persistence").error("Failed to save event: %s", e)

    def close(self):
        if self._conn:
            self._conn.close()
