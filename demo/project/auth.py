"""Authentication module — CONTAINS A DELIBERATE BUG.

Bug: Line 16 reads ``config.AUTH_SECRET_KEY`` instead of ``config.SECRET_KEY``.
This causes a ``KeyError`` / ``AttributeError`` that makes all authentication
fail with a 401 error.

KALKI should:
  1. Read this file
  2. Identify the wrong attribute name
  3. Fix it to ``config.SECRET_KEY``
  4. Verify the fix with tests
"""
import hashlib
import time

import config


def create_token(user_id: str) -> str:
    """Create a simple auth token for a user."""
    # BUG: should be config.SECRET_KEY, not config.AUTH_SECRET_KEY
    secret = config.AUTH_SECRET_KEY  # <-- THIS IS THE BUG
    timestamp = str(int(time.time()))
    payload = f"{user_id}:{timestamp}"
    signature = hashlib.sha256(f"{payload}:{secret}".encode()).hexdigest()[:16]
    return f"{payload}:{signature}"


def verify_token(token: str) -> dict:
    """Verify a token and return the user info."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return {"valid": False, "error": "malformed token"}
        user_id, timestamp, signature = parts
        # BUG: should be config.SECRET_KEY, not config.AUTH_SECRET_KEY
        secret = config.AUTH_SECRET_KEY  # <-- THIS IS THE BUG
        expected = hashlib.sha256(f"{user_id}:{timestamp}:{secret}".encode()).hexdigest()[:16]
        if signature != expected:
            return {"valid": False, "error": "invalid signature"}
        return {"valid": True, "user_id": user_id}
    except Exception as e:
        return {"valid": False, "error": str(e)}
