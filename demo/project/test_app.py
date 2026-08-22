"""Tests for the demo app — these FAIL until the auth bug is fixed.

The test ``test_login_and_access`` calls ``login()`` which calls
``create_token()`` which references ``config.AUTH_SECRET_KEY`` (does not
exist), causing an ``AttributeError``.  Once the bug is fixed to use
``config.SECRET_KEY``, all tests pass.
"""
import sys
import os

# Ensure the repo root is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from app import get_public_info, get_protected_data, login


def test_public_info():
    """Public endpoint should always work."""
    result = get_public_info()
    assert result["status"] == "running"
    assert result["app"] == "KALKI Demo App"


def test_login_and_access():
    """Login should create a token, and that token should grant access.

    THIS TEST FAILS due to the auth bug (config.AUTH_SECRET_KEY does not
    exist in config.py — it should be config.SECRET_KEY).
    """
    # Step 1: Login
    login_result = login("user-42")
    assert login_result["status"] == 200, f"Login failed: {login_result}"
    assert "token" in login_result

    # Step 2: Access protected data with the token
    token = login_result["token"]
    data = get_protected_data(token)
    assert data["status"] == 200, f"Access denied: {data}"
    assert data["user_id"] == "user-42"


def test_invalid_token_rejected():
    """An invalid token should be rejected."""
    result = get_protected_data("invalid:token:here")
    assert result["status"] == 401


def test_malformed_token_rejected():
    """A malformed token should be rejected."""
    result = get_protected_data("no-colons")
    assert result["status"] == 401
