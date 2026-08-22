import pytest
from unittest.mock import patch, MagicMock
from backend.persistence import RunStore
from config.settings import Settings
from shared.contracts import AgentState
from api.app import get_current_user
from fastapi import HTTPException
import jwt

def test_run_store_no_db():
    settings = Settings(memory_backend="local", supabase_db_url="")
    store = RunStore(settings)
    assert store._conn is None
    
    # Should not crash
    state = AgentState(objective="test")
    store.save_state(state)

def test_get_current_user_no_auth_header():
    req = MagicMock()
    req.headers.get.return_value = None
    assert get_current_user(req) is None

def test_get_current_user_invalid_token():
    req = MagicMock()
    req.headers.get.return_value = "Bearer invalid.token"
    req.app.state.service.settings.supabase_jwt_secret = "secret"
    
    with pytest.raises(HTTPException) as exc:
        get_current_user(req)
    assert exc.value.status_code == 401

def test_get_current_user_valid_token():
    req = MagicMock()
    token = jwt.encode({"sub": "user-123", "aud": "authenticated"}, "secret", algorithm="HS256")
    req.headers.get.return_value = f"Bearer {token}"
    req.app.state.service.settings.supabase_jwt_secret = "secret"
    
    user_id = get_current_user(req)
    assert user_id == "user-123"

def test_supabase_store_enforces_user_id():
    from shared.contracts import MemoryRecord, MemoryScope
    from memory.supabase_store import SupabaseMemoryStore
    store = object.__new__(SupabaseMemoryStore)
    record = MemoryRecord(id="1", scope=MemoryScope.SESSION, content="test", user_id=None)
    with pytest.raises(ValueError, match="user_id is required"):
        store.add(record)
