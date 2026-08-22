"""Run, event, and integration persistence layer."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from typing import Any, Optional

from config.settings import Settings
from shared.contracts import AgentEvent, AgentState

log = logging.getLogger("kalki.persistence")


def encrypt_token(plain_text: str, secret_key: str) -> str:
    """Encrypt a secret token at rest using HMAC-SHA256 counter mode keystream."""
    if not plain_text:
        return ""
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    iv = secrets.token_bytes(16)
    data = plain_text.encode("utf-8")
    
    # Generate keystream block by block
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(data):
        block = hmac.new(key, iv + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        keystream.extend(block)
        counter += 1
        
    cipher = bytes([d ^ k for d, k in zip(data, keystream[:len(data)])])
    # Payload: 16 bytes IV + cipher
    payload = iv + cipher
    # Auth tag
    tag = hmac.new(key, b"auth:" + payload, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(tag + payload).decode("ascii")


def decrypt_token(cipher_text: str, secret_key: str) -> str:
    """Decrypt a token previously encrypted with encrypt_token."""
    if not cipher_text:
        return ""
    try:
        raw = base64.urlsafe_b64decode(cipher_text.encode("ascii"))
        if len(raw) < 32:
            return ""
        tag = raw[:16]
        payload = raw[16:]
        key = hashlib.sha256(secret_key.encode("utf-8")).digest()
        expected_tag = hmac.new(key, b"auth:" + payload, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            log.warning("Decryption failed: HMAC authentication tag mismatch")
            return ""
        
        iv = payload[:16]
        cipher = payload[16:]
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(cipher):
            block = hmac.new(key, iv + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            keystream.extend(block)
            counter += 1
            
        plain = bytes([c ^ k for c, k in zip(cipher, keystream[:len(cipher)])])
        return plain.decode("utf-8")
    except Exception as e:
        log.warning("Token decryption error: %s", e)
        return ""


class RunStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._conn = None
        if self.settings.memory_backend == "supabase" and self.settings.supabase_db_url:
            try:
                import psycopg  # type: ignore
                self._conn = psycopg.connect(self.settings.supabase_db_url, autocommit=True)
            except Exception as e:
                log.warning("RunStore DB connection failed: %s", e)
                
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
            log.error("Failed to save state: %s", e)

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
            log.error("Failed to save event: %s", e)

    def close(self):
        if self._conn:
            self._conn.close()


class IntegrationStore:
    """Store for managing per-user OAuth credentials, Vercel tokens, and local projects."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._mem_integrations: dict[tuple[str, str], dict[str, Any]] = {}
        self._mem_local_projects: dict[str, list[dict[str, Any]]] = {}
        self._mem_kalki_projects: dict[str, list[dict[str, Any]]] = {}
        self._conn = None
        if self.settings.memory_backend == "supabase" and self.settings.supabase_db_url:
            try:
                import psycopg  # type: ignore
                self._conn = psycopg.connect(self.settings.supabase_db_url, autocommit=True)
            except Exception as e:
                log.warning("IntegrationStore DB connection failed (falling back to memory): %s", e)

    def _enc_key(self) -> str:
        return self.settings.encryption_key or self.settings.supabase_jwt_secret or "kalki-dev-key"

    def save_integration(self, user_id: str, provider: str, token: str,
                         account_id: str = "", account_username: str = "",
                         scopes: list[str] | None = None,
                         metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Encrypts token and saves integration connection."""
        enc_token = encrypt_token(token, self._enc_key())
        record = {
            "id": f"{user_id}:{provider}",
            "user_id": user_id,
            "provider": provider,
            "account_id": account_id,
            "account_username": account_username,
            "encrypted_token": enc_token,
            "scopes": scopes or [],
            "metadata": metadata or {},
            "updated_at": time.time(),
        }
        with self._lock:
            self._mem_integrations[(user_id, provider)] = record

        if self._conn and user_id:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO user_integrations
                           (id, user_id, provider, account_id, account_username, encrypted_token, scopes, metadata, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                           ON CONFLICT (user_id, provider) DO UPDATE SET
                           account_id=EXCLUDED.account_id, account_username=EXCLUDED.account_username,
                           encrypted_token=EXCLUDED.encrypted_token, scopes=EXCLUDED.scopes,
                           metadata=EXCLUDED.metadata, updated_at=now()""",
                        (record["id"], user_id, provider, account_id, account_username,
                         enc_token, json.dumps(scopes or []), json.dumps(metadata or {}))
                    )
            except Exception as e:
                log.error("Failed to persist user integration: %s", e)
        return record

    def get_integration(self, user_id: str, provider: str) -> dict[str, Any] | None:
        """Retrieves and decrypts the integration token for the user."""
        record = None
        with self._lock:
            record = self._mem_integrations.get((user_id, provider))

        if not record and self._conn and user_id:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, user_id, provider, account_id, account_username, encrypted_token, scopes, metadata
                           FROM user_integrations WHERE user_id = %s AND provider = %s""",
                        (user_id, provider)
                    )
                    row = cur.fetchone()
                    if row:
                        record = {
                            "id": row[0], "user_id": str(row[1]), "provider": row[2],
                            "account_id": row[3], "account_username": row[4],
                            "encrypted_token": row[5],
                            "scopes": row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]"),
                            "metadata": row[7] if isinstance(row[7], dict) else json.loads(row[7] or "{}"),
                        }
                        with self._lock:
                            self._mem_integrations[(user_id, provider)] = record
            except Exception as e:
                log.error("Failed to query user integration: %s", e)

        if not record:
            return None

        # Decrypt token for internal server usage (never returned to browser)
        decrypted = decrypt_token(record["encrypted_token"], self._enc_key())
        return {
            "user_id": record["user_id"],
            "provider": record["provider"],
            "account_id": record.get("account_id", ""),
            "account_username": record.get("account_username", ""),
            "token": decrypted,
            "scopes": record.get("scopes", []),
            "metadata": record.get("metadata", {}),
        }

    def delete_integration(self, user_id: str, provider: str) -> bool:
        """Revokes/deletes user integration credentials."""
        with self._lock:
            self._mem_integrations.pop((user_id, provider), None)

        if self._conn and user_id:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM user_integrations WHERE user_id = %s AND provider = %s",
                        (user_id, provider)
                    )
            except Exception as e:
                log.error("Failed to delete user integration: %s", e)
        return True

    def list_integrations(self, user_id: str) -> list[dict[str, Any]]:
        """Returns safe integration statuses (without sensitive tokens)."""
        providers = ["github", "vercel"]
        res = []
        for p in providers:
            integ = self.get_integration(user_id, p)
            if integ and integ.get("token"):
                res.append({
                    "provider": p,
                    "connected": True,
                    "account_username": integ.get("account_username", ""),
                    "account_id": integ.get("account_id", ""),
                    "metadata": integ.get("metadata", {}),
                })
            else:
                res.append({
                    "provider": p,
                    "connected": False,
                    "account_username": "",
                    "account_id": "",
                    "metadata": {},
                })
        return res

    # ── Local Projects ──────────────────────────────────────────
    def save_local_project(self, user_id: str, name: str, local_path: str,
                           git_remote: str = "", current_branch: str = "main",
                           status: str = "connected",
                           metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        project_id = hashlib.sha256(f"{user_id}:{local_path}".encode()).hexdigest()[:12]
        item = {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "local_path": local_path,
            "git_remote": git_remote,
            "current_branch": current_branch,
            "status": status,
            "metadata": metadata or {},
            "updated_at": time.time(),
        }
        with self._lock:
            projects = self._mem_local_projects.setdefault(user_id, [])
            # update existing or append
            for i, p in enumerate(projects):
                if p["id"] == project_id:
                    projects[i] = item
                    break
            else:
                projects.append(item)

        if self._conn and user_id:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO local_projects
                           (id, user_id, name, local_path, git_remote, current_branch, status, metadata, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                           ON CONFLICT (id) DO UPDATE SET
                           name=EXCLUDED.name, git_remote=EXCLUDED.git_remote,
                           current_branch=EXCLUDED.current_branch, status=EXCLUDED.status,
                           metadata=EXCLUDED.metadata, updated_at=now()""",
                        (project_id, user_id, name, local_path, git_remote,
                         current_branch, status, json.dumps(metadata or {}))
                    )
            except Exception as e:
                log.error("Failed to persist local project: %s", e)
        return item

    def list_local_projects(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._mem_local_projects.get(user_id, []))

    def delete_local_project(self, user_id: str, project_id: str) -> bool:
        with self._lock:
            projects = self._mem_local_projects.get(user_id, [])
            self._mem_local_projects[user_id] = [p for p in projects if p["id"] != project_id]
        if self._conn and user_id:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("DELETE FROM local_projects WHERE id = %s AND user_id = %s", (project_id, user_id))
            except Exception as e:
                log.error("Failed to delete local project: %s", e)
        return True

    def close(self):
        if self._conn:
            self._conn.close()

