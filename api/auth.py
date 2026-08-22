"""Google Authentication and User Identity routes for KALKI."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from config.settings import Settings

log = logging.getLogger("kalki.auth")

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_secret(settings: Settings) -> str:
    return settings.supabase_jwt_secret or settings.encryption_key or "kalki-dev-auth-secret-32b"


def create_session_jwt(user_id: str, email: str, name: str, avatar_url: str, settings: Settings) -> str:
    """Create a signed KALKI JWT session token."""
    secret = _get_secret(settings)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "avatar_url": avatar_url,
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + (86400 * 30),  # 30-day session
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def generate_oauth_state(secret: str) -> str:
    """Generate a tamper-proof state string for CSRF protection."""
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{ts}:{sig}"


def verify_oauth_state(state: str, secret: str, max_age_secs: int = 600) -> bool:
    """Verify the validity and expiry of an OAuth state string."""
    try:
        ts_str, sig = state.split(":", 1)
        ts = int(ts_str)
        if time.time() - ts > max_age_secs or time.time() < ts - 60:
            return False
        expected_sig = hmac.new(secret.encode(), ts_str.encode(), hashlib.sha256).hexdigest()[:16]
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


def get_current_user_payload(req: Request) -> Optional[dict[str, Any]]:
    """Dependency to extract authenticated user payload from Bearer token."""
    auth = req.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth.split(" ")[1]
    svc = req.app.state.service
    secret = _get_secret(svc.settings)
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        return payload
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


# ── Google OAuth Endpoints ──────────────────────────────────────────

@auth_router.get("/google/login")
def google_login(req: Request):
    """Initiates Google OAuth 2.0 flow."""
    svc = req.app.state.service
    settings: Settings = svc.settings
    
    if not settings.google_client_id:
        raise HTTPException(500, "Google OAuth not configured. Please set GOOGLE_CLIENT_ID in environment.")

    # Calculate callback URL
    host = req.headers.get("host", "localhost:8000")
    proto = req.headers.get("x-forwarded-proto", "http" if "localhost" in host else "https")
    redirect_uri = f"{proto}://{host}/api/auth/google/callback"
    
    state = generate_oauth_state(_get_secret(settings))
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@auth_router.get("/google/callback")
def google_callback(req: Request, code: Optional[str] = Query(None), state: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handles Google OAuth callback, exchanges code for user profile and issues JWT."""
    if error:
        return RedirectResponse(url=f"/?auth_error={urllib.parse.quote(error)}")
    if not code or not state:
        return RedirectResponse(url="/?auth_error=missing_code_or_state")
        
    svc = req.app.state.service
    settings: Settings = svc.settings
    secret = _get_secret(settings)
    
    if not verify_oauth_state(state, secret):
        return RedirectResponse(url="/?auth_error=invalid_or_expired_state")
        
    host = req.headers.get("host", "localhost:8000")
    proto = req.headers.get("x-forwarded-proto", "http" if "localhost" in host else "https")
    redirect_uri = f"{proto}://{host}/api/auth/google/callback"

    # 1. Exchange code for access token
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    
    token_req = urllib.request.Request(
        token_url,
        data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(token_req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
            access_token = token_data.get("access_token")
    except Exception as e:
        log.error("Google token exchange failed: %s", e)
        return RedirectResponse(url=f"/?auth_error=token_exchange_failed")

    # 2. Fetch Google User Profile
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    userinfo_req = urllib.request.Request(
        userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(userinfo_req, timeout=15) as resp:
            user_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.error("Google userinfo fetch failed: %s", e)
        return RedirectResponse(url=f"/?auth_error=profile_fetch_failed")

    google_id = user_data.get("id")
    email = user_data.get("email", "")
    name = user_data.get("name", "Google Developer")
    picture = user_data.get("picture", "")
    
    # Deterministic or Supabase compatible User ID
    user_id = f"google:{google_id}"
    
    # 3. Create session JWT
    session_token = create_session_jwt(
        user_id=user_id,
        email=email,
        name=name,
        avatar_url=picture,
        settings=settings
    )
    
    return RedirectResponse(url=f"/?token={session_token}&login=success")


# ── Guest & Session Endpoints ───────────────────────────────────────

@auth_router.post("/guest")
def guest_login(req: Request):
    """Issues a local developer guest session."""
    svc = req.app.state.service
    token = create_session_jwt(
        user_id="guest-developer",
        email="developer@kalki.local",
        name="Guest Developer (Local)",
        avatar_url="",
        settings=svc.settings
    )
    return {
        "token": token,
        "user": {
            "id": "guest-developer",
            "email": "developer@kalki.local",
            "name": "Guest Developer (Local)",
            "avatar_url": "",
        }
    }


@auth_router.get("/me")
def get_me(user: Optional[dict[str, Any]] = Depends(get_current_user_payload)):
    """Returns the authenticated KALKI user profile."""
    if not user:
        return {
            "authenticated": False,
            "user": None
        }
    return {
        "authenticated": True,
        "user": {
            "id": user.get("sub"),
            "email": user.get("email"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
        }
    }
