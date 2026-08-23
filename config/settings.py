"""Central configuration for KALKI.

Loads from environment variables (optionally seeded by a local ``.env``)
with safe, offline-first defaults. No third-party dependency: the ``.env``
parser here is a tiny stdlib helper so the core never needs python-dotenv.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    """Minimal ``.env`` loader. Does not override already-set env vars."""
    p = Path(path)
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable resolved configuration snapshot."""

    # Model routing
    model_provider: str = "mock"
    model_name: str = "claude-sonnet-4"
    omniroute_base_url: str = "http://localhost:20128"
    omniroute_api_key: str = ""
    omniroute_health_path: str = ""   # blank -> provider probes /v1/models
    huggingface_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""
    mistral_agent_id: str = ""

    # Memory
    memory_backend: str = "local"
    local_db_path: str = "kalki_local.sqlite3"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_db_url: str = ""
    embedding_dim: int = 384

    # Execution / safety
    autonomy: str = "supervised"          # supervised | autonomous
    max_task_retries: int = 2
    max_plan_revisions: int = 3
    workspace_root: str = "."

    # API & Networking
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "INFO"
    app_base_url: str = "http://localhost:8000"

    # Integrations & Auth
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    vercel_client_id: str = ""
    vercel_client_secret: str = ""
    encryption_key: str = ""

    # Non-config runtime metadata
    extras: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, load_dotenv: bool = True) -> "Settings":
        if load_dotenv:
            _load_dotenv()
        return cls(
            model_provider=_get("KALKI_MODEL_PROVIDER", "mock").lower(),
            model_name=_get("KALKI_MODEL_NAME", "claude-sonnet-4"),
            omniroute_base_url=_get("OMNIROUTE_BASE_URL", "http://localhost:20128"),
            omniroute_api_key=_get("OMNIROUTE_API_KEY", ""),
            omniroute_health_path=_get("OMNIROUTE_HEALTH_PATH", ""),
            huggingface_api_key=_get("HUGGINGFACE_API_KEY", _get("HF_TOKEN", "")),
            anthropic_api_key=_get("ANTHROPIC_API_KEY", ""),
            openai_api_key=_get("OPENAI_API_KEY", ""),
            gemini_api_key=_get("GEMINI_API_KEY", ""),
            mistral_api_key=_get("MISTRAL_API_KEY", ""),
            mistral_agent_id=_get("MISTRAL_AGENT_ID", ""),
            memory_backend=_get("KALKI_MEMORY_BACKEND", "local").lower(),
            local_db_path=_get("KALKI_LOCAL_DB_PATH", "kalki_local.sqlite3"),
            supabase_url=_get("SUPABASE_URL", ""),
            supabase_service_role_key=_get("SUPABASE_SERVICE_ROLE_KEY", ""),
            supabase_jwt_secret=_get("SUPABASE_JWT_SECRET", ""),
            supabase_db_url=_get("SUPABASE_DB_URL", ""),
            embedding_dim=_get_int("KALKI_EMBEDDING_DIM", 384),
            autonomy=_get("KALKI_AUTONOMY", "supervised").lower(),
            max_task_retries=_get_int("KALKI_MAX_TASK_RETRIES", 2),
            max_plan_revisions=_get_int("KALKI_MAX_PLAN_REVISIONS", 3),
            workspace_root=_get("KALKI_WORKSPACE_ROOT", "."),
            api_host=_get("KALKI_API_HOST", "127.0.0.1"),
            api_port=_get_int("KALKI_API_PORT", 8000),
            log_level=_get("KALKI_LOG_LEVEL", "INFO"),
            app_base_url=_get("APP_BASE_URL", _get("KALKI_APP_BASE_URL", "http://localhost:8000")),
            google_client_id=_get("GOOGLE_CLIENT_ID", ""),
            google_client_secret=_get("GOOGLE_CLIENT_SECRET", ""),
            github_client_id=_get("GITHUB_CLIENT_ID", ""),
            github_client_secret=_get("GITHUB_CLIENT_SECRET", ""),
            vercel_client_id=_get("VERCEL_CLIENT_ID", ""),
            vercel_client_secret=_get("VERCEL_CLIENT_SECRET", ""),
            encryption_key=_get("ENCRYPTION_KEY", _get("SUPABASE_JWT_SECRET", "kalki-default-dev-secret-key-32b")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached settings. Call ``get_settings.cache_clear()`` in
    tests that mutate the environment."""
    return Settings.from_env()
