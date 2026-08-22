"""Tests for Google Auth, GitHub OAuth, Vercel Integrations, and Local CLI Protocol."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from fastapi.testclient import TestClient

from api.app import create_app
from api.auth import create_session_jwt, generate_oauth_state, verify_oauth_state
from backend.persistence import decrypt_token, encrypt_token
from backend.service import KalkiService
from config.settings import Settings


@pytest.fixture()
def custom_settings():
    return Settings(
        google_client_id="test_google_client_id",
        google_client_secret="test_google_client_secret",
        github_client_id="test_github_client_id",
        github_client_secret="test_github_client_secret",
        encryption_key="test-symmetric-encryption-key-32b",
        supabase_jwt_secret="test-jwt-secret-key-32b",
        app_base_url="http://localhost:8000",
        memory_backend="local",
        supabase_db_url="",
    )


@pytest.fixture()
def client(custom_settings):
    svc = KalkiService(settings=custom_settings)
    app = create_app(svc)
    return TestClient(app)


# ── 1. Encryption & Token Security ──────────────────────────────────

def test_token_encryption_roundtrip():
    key = "super-secret-key-for-kalki"
    token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = encrypt_token(token, key)
    assert encrypted != token
    decrypted = decrypt_token(encrypted, key)
    assert decrypted == token


def test_token_decryption_with_wrong_key_fails():
    token = "vcp_12345secret"
    encrypted = encrypt_token(token, "correct-key")
    decrypted = decrypt_token(encrypted, "wrong-key")
    assert decrypted == ""


# ── 2. OAuth State Verification ─────────────────────────────────────

def test_oauth_state_generation_and_verification():
    secret = "kalki-state-secret"
    state = generate_oauth_state(secret)
    assert verify_oauth_state(state, secret) is True
    assert verify_oauth_state(state, "wrong-secret") is False
    assert verify_oauth_state("invalid:tampered", secret) is False


# ── 3. Google Auth & Session Endpoints ──────────────────────────────

def test_google_login_redirect(client):
    res = client.get("/api/auth/google/login", follow_redirects=False)
    assert res.status_code == 307
    location = res.headers["location"]
    assert "accounts.google.com/o/oauth2/v2/auth" in location
    assert "client_id=test_google_client_id" in location
    assert "scope=openid+email+profile" in location


def test_guest_login_and_me_endpoint(client):
    res = client.post("/api/auth/guest")
    assert res.status_code == 200
    data = res.json()
    token = data["token"]
    assert token

    # Test /api/auth/me with Bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["authenticated"] is True
    assert me_data["user"]["id"] == "guest-developer"


# ── 4. GitHub Integration ───────────────────────────────────────────

def test_github_connect_and_status(client, custom_settings):
    user_token = create_session_jwt("user-alice", "alice@example.com", "Alice", "", custom_settings)
    auth_header = {"Authorization": f"Bearer {user_token}"}

    # 1. Check initial disconnected status
    status_res = client.get("/api/integrations/github/status", headers=auth_header)
    assert status_res.status_code == 200
    assert status_res.json()["connected"] is False

    # 2. Connect URL generation
    connect_res = client.get("/api/integrations/github/connect", headers=auth_header, follow_redirects=False)
    assert connect_res.status_code == 307
    location = connect_res.headers["location"]
    assert "github.com/login/oauth/authorize" in location
    assert "client_id=test_github_client_id" in location

    # 3. Simulate stored integration (as would happen via callback)
    app = client.app
    svc = app.state.service
    svc.integration_store.save_integration(
        user_id="user-alice",
        provider="github",
        token="gho_test_token_123",
        account_username="alice_dev",
        scopes=["read:user", "repo"]
    )

    # 4. Status is now connected
    status_res2 = client.get("/api/integrations/github/status", headers=auth_header)
    assert status_res2.status_code == 200
    data2 = status_res2.json()
    assert data2["connected"] is True
    assert data2["username"] == "alice_dev"

    # 5. Disconnect
    disc_res = client.post("/api/integrations/github/disconnect", headers=auth_header)
    assert disc_res.status_code == 200
    status_res3 = client.get("/api/integrations/github/status", headers=auth_header)
    assert status_res3.json()["connected"] is False


# ── 5. Vercel Integration ───────────────────────────────────────────

def test_vercel_connect_and_disconnect(client, custom_settings):
    user_token = create_session_jwt("user-bob", "bob@example.com", "Bob", "", custom_settings)
    auth_header = {"Authorization": f"Bearer {user_token}"}

    # Initial status
    status_res = client.get("/api/integrations/vercel/status", headers=auth_header)
    assert status_res.status_code == 200
    assert status_res.json()["connected"] is False

    # Mock Vercel API user verification call
    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"user": {"id": "v_123", "username": "bob_vercel", "email": "bob@example.com"}}).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        connect_res = client.post("/api/integrations/vercel/connect", json={"token": "vcp_valid_token"}, headers=auth_header)
        assert connect_res.status_code == 200
        assert connect_res.json()["connected"] is True
        assert connect_res.json()["username"] == "bob_vercel"

    # Verify status
    status_res2 = client.get("/api/integrations/vercel/status", headers=auth_header)
    assert status_res2.json()["connected"] is True
    assert status_res2.json()["username"] == "bob_vercel"

    # Disconnect
    disc_res = client.post("/api/integrations/vercel/disconnect", headers=auth_header)
    assert disc_res.status_code == 200
    status_res3 = client.get("/api/integrations/vercel/status", headers=auth_header)
    assert status_res3.json()["connected"] is False


# ── 6. Local CLI Repository Protocol ────────────────────────────────

def test_local_repository_connect_and_list(client, custom_settings):
    user_token = create_session_jwt("user-charlie", "charlie@example.com", "Charlie", "", custom_settings)
    auth_header = {"Authorization": f"Bearer {user_token}"}

    # Register a local project
    connect_res = client.post("/api/integrations/local/connect", json={
        "name": "My Local Project",
        "path": "/home/dev/my-project",
        "git_remote": "git@github.com:charlie/my-project.git",
        "current_branch": "feat/agent",
        "status": "connected"
    }, headers=auth_header)
    assert connect_res.status_code == 200
    project = connect_res.json()["project"]
    assert project["name"] == "My Local Project"
    project_id = project["id"]

    # List local projects
    list_res = client.get("/api/integrations/local/projects", headers=auth_header)
    assert list_res.status_code == 200
    projs = list_res.json()["projects"]
    assert len(projs) == 1
    assert projs[0]["id"] == project_id

    # Disconnect local project
    disc_res = client.post("/api/integrations/local/disconnect", json={"project_id": project_id}, headers=auth_header)
    assert disc_res.status_code == 200
    list_res2 = client.get("/api/integrations/local/projects", headers=auth_header)
    assert len(list_res2.json()["projects"]) == 0


# ── 7. Multi-User Isolation ─────────────────────────────────────────

def test_user_isolation_between_integrations(client, custom_settings):
    token_user_a = create_session_jwt("user-a", "a@test.com", "User A", "", custom_settings)
    token_user_b = create_session_jwt("user-b", "b@test.com", "User B", "", custom_settings)

    svc = client.app.state.service

    # User A connects GitHub
    svc.integration_store.save_integration(
        user_id="user-a",
        provider="github",
        token="token_a",
        account_username="user_a_github"
    )

    # User B should see GitHub as disconnected
    res_b = client.get("/api/integrations/github/status", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_b.json()["connected"] is False

    # User A sees GitHub as connected
    res_a = client.get("/api/integrations/github/status", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res_a.json()["connected"] is True
    assert res_a.json()["username"] == "user_a_github"
