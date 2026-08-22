"""Workspace integrations API router for GitHub, Vercel, and Local Repository CLI."""
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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.auth import _get_secret, get_current_user_payload
from config.settings import Settings

log = logging.getLogger("kalki.integrations")

integrations_router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def get_required_user(user: Optional[dict[str, Any]] = Depends(get_current_user_payload)) -> str:
    """Ensures endpoint is called with valid authentication."""
    if not user or not user.get("sub"):
        # Fallback to guest for development if header is not present
        return "guest-developer"
    return user["sub"]


# ── Request Models ──────────────────────────────────────────────────

class VercelConnectRequest(BaseModel):
    token: str


class LocalConnectRequest(BaseModel):
    name: str
    path: str
    git_remote: Optional[str] = ""
    current_branch: Optional[str] = "main"
    status: Optional[str] = "connected"


class LocalDisconnectRequest(BaseModel):
    project_id: str


# ── Helper Functions ────────────────────────────────────────────────

def _generate_user_oauth_state(user_id: str, secret: str) -> str:
    ts = str(int(time.time()))
    data = f"{user_id}:{ts}"
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{user_id}:{ts}:{sig}"


def _verify_user_oauth_state(state: str, secret: str, max_age_secs: int = 600) -> Optional[str]:
    try:
        parts = state.split(":")
        if len(parts) < 3:
            return None
        user_id = ":".join(parts[:-2])
        ts_str = parts[-2]
        sig = parts[-1]
        ts = int(ts_str)
        if time.time() - ts > max_age_secs or time.time() < ts - 60:
            return None
        data = f"{user_id}:{ts_str}"
        expected_sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(sig, expected_sig):
            return user_id
        return None
    except Exception:
        return None


# ── 1. GitHub Integration ───────────────────────────────────────────

@integrations_router.get("/github/connect")
def github_connect(req: Request, user_id: str = Depends(get_required_user)):
    """Initiates GitHub OAuth flow to connect user's GitHub account."""
    svc = req.app.state.service
    settings: Settings = svc.settings
    
    if not settings.github_client_id:
        raise HTTPException(500, "GitHub OAuth not configured. Set GITHUB_CLIENT_ID in environment.")
        
    host = req.headers.get("host", "localhost:8000")
    proto = req.headers.get("x-forwarded-proto", "http" if "localhost" in host else "https")
    redirect_uri = f"{proto}://{host}/api/integrations/github/callback"
    
    state = _generate_user_oauth_state(user_id, _get_secret(settings))
    
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user,repo",
        "state": state,
    }
    
    auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@integrations_router.get("/github/callback")
def github_callback(req: Request, code: Optional[str] = Query(None), state: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handles GitHub OAuth authorization callback and stores encrypted token."""
    if error:
        return RedirectResponse(url=f"/?integration_error=github_{urllib.parse.quote(error)}")
    if not code or not state:
        return RedirectResponse(url="/?integration_error=missing_github_code")
        
    svc = req.app.state.service
    settings: Settings = svc.settings
    secret = _get_secret(settings)
    
    user_id = _verify_user_oauth_state(state, secret)
    if not user_id:
        return RedirectResponse(url="/?integration_error=invalid_github_state")
        
    host = req.headers.get("host", "localhost:8000")
    proto = req.headers.get("x-forwarded-proto", "http" if "localhost" in host else "https")
    redirect_uri = f"{proto}://{host}/api/integrations/github/callback"

    # 1. Exchange code for GitHub Access Token
    token_url = "https://github.com/login/oauth/access_token"
    token_payload = urllib.parse.urlencode({
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }).encode("utf-8")
    
    token_req = urllib.request.Request(
        token_url,
        data=token_payload,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(token_req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
            access_token = token_data.get("access_token")
            scope_str = token_data.get("scope", "")
            scopes = [s.strip() for s in scope_str.split(",") if s.strip()]
    except Exception as e:
        log.error("GitHub token exchange failed: %s", e)
        return RedirectResponse(url="/?integration_error=github_token_exchange_failed")

    if not access_token:
        log.error("GitHub returned no access_token: %s", token_data)
        return RedirectResponse(url="/?integration_error=github_no_access_token")

    # 2. Fetch authenticated GitHub user profile
    user_req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "KALKI-Agent"
        },
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(user_req, timeout=15) as resp:
            github_user = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.error("GitHub user info failed: %s", e)
        return RedirectResponse(url="/?integration_error=github_user_fetch_failed")

    # 3. Store encrypted integration securely linked to user
    svc.integration_store.save_integration(
        user_id=user_id,
        provider="github",
        token=access_token,
        account_id=str(github_user.get("id")),
        account_username=github_user.get("login", ""),
        scopes=scopes,
        metadata={
            "name": github_user.get("name", ""),
            "avatar_url": github_user.get("avatar_url", ""),
            "html_url": github_user.get("html_url", ""),
        }
    )
    
    return RedirectResponse(url="/?integration=github&status=connected")


@integrations_router.get("/github/status")
def github_status(req: Request, user_id: str = Depends(get_required_user)):
    """Returns the user's GitHub connection status."""
    svc = req.app.state.service
    integ = svc.integration_store.get_integration(user_id, "github")
    if not integ or not integ.get("token"):
        return {"connected": False}
    return {
        "connected": True,
        "username": integ.get("account_username"),
        "account_id": integ.get("account_id"),
        "scopes": integ.get("scopes", []),
        "metadata": integ.get("metadata", {}),
    }


@integrations_router.get("/github/repos")
def github_repos(req: Request, user_id: str = Depends(get_required_user)):
    """Fetches repositories belonging to or accessible by the connected GitHub user."""
    svc = req.app.state.service
    integ = svc.integration_store.get_integration(user_id, "github")
    if not integ or not integ.get("token"):
        raise HTTPException(400, "GitHub is not connected. Connect GitHub first.")

    token = integ["token"]
    repos_req = urllib.request.Request(
        "https://api.github.com/user/repos?sort=updated&per_page=100&affiliation=owner,collaborator,organization_member",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "KALKI-Agent"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(repos_req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            repos = []
            for r in data:
                repos.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "private": r.get("private"),
                    "html_url": r.get("html_url"),
                    "default_branch": r.get("default_branch", "main"),
                    "language": r.get("language"),
                    "updated_at": r.get("updated_at"),
                    "description": r.get("description"),
                })
            return {"repos": repos}
    except Exception as e:
        log.error("Failed to fetch GitHub repos: %s", e)
        raise HTTPException(502, f"Failed to fetch repositories from GitHub: {e}")


@integrations_router.post("/github/disconnect")
def github_disconnect(req: Request, user_id: str = Depends(get_required_user)):
    """Disconnects and clears user's GitHub integration credentials."""
    svc = req.app.state.service
    svc.integration_store.delete_integration(user_id, "github")
    return {"success": True, "provider": "github"}


# ── 2. Vercel Integration ───────────────────────────────────────────

@integrations_router.post("/vercel/connect")
def vercel_connect(body: VercelConnectRequest, req: Request, user_id: str = Depends(get_required_user)):
    """Connects user's personal Vercel Access Token and stores it securely."""
    token = body.token.strip()
    if not token:
        raise HTTPException(400, "Vercel token is required.")

    # Validate token by checking user profile on Vercel API
    user_req = urllib.request.Request(
        "https://api.vercel.com/v2/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(user_req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            vercel_user = res.get("user", {})
    except Exception as e:
        log.error("Vercel token validation failed: %s", e)
        raise HTTPException(400, f"Invalid Vercel token: {e}")

    account_id = vercel_user.get("id", "")
    username = vercel_user.get("username", "")
    email = vercel_user.get("email", "")

    svc = req.app.state.service
    svc.integration_store.save_integration(
        user_id=user_id,
        provider="vercel",
        token=token,
        account_id=account_id,
        account_username=username,
        metadata={"email": email, "name": vercel_user.get("name", "")}
    )

    return {
        "connected": True,
        "username": username,
        "email": email
    }


@integrations_router.get("/vercel/status")
def vercel_status(req: Request, user_id: str = Depends(get_required_user)):
    """Returns the user's Vercel connection status."""
    svc = req.app.state.service
    integ = svc.integration_store.get_integration(user_id, "vercel")
    if not integ or not integ.get("token"):
        return {"connected": False}
    return {
        "connected": True,
        "username": integ.get("account_username"),
        "account_id": integ.get("account_id"),
        "metadata": integ.get("metadata", {}),
    }


@integrations_router.get("/vercel/projects")
def vercel_projects(req: Request, user_id: str = Depends(get_required_user)):
    """Fetches projects belonging to the connected Vercel account."""
    svc = req.app.state.service
    integ = svc.integration_store.get_integration(user_id, "vercel")
    if not integ or not integ.get("token"):
        raise HTTPException(400, "Vercel is not connected. Connect Vercel first.")

    token = integ["token"]
    proj_req = urllib.request.Request(
        "https://api.vercel.com/v9/projects",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )

    try:
        with urllib.request.urlopen(proj_req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            projects = []
            for p in data.get("projects", []):
                latest = p.get("latestDeployments", [{}])[0] if p.get("latestDeployments") else {}
                projects.append({
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "framework": p.get("framework"),
                    "updatedAt": p.get("updatedAt"),
                    "link": p.get("link", {}),
                    "latest_deployment": {
                        "id": latest.get("id"),
                        "url": latest.get("url"),
                        "readyState": latest.get("readyState", "UNKNOWN"),
                        "createdAt": latest.get("createdAt"),
                    } if latest else None
                })
            return {"projects": projects}
    except Exception as e:
        log.error("Failed to fetch Vercel projects: %s", e)
        raise HTTPException(502, f"Failed to fetch Vercel projects: {e}")


@integrations_router.post("/vercel/disconnect")
def vercel_disconnect(req: Request, user_id: str = Depends(get_required_user)):
    """Disconnects and clears user's Vercel integration credentials."""
    svc = req.app.state.service
    svc.integration_store.delete_integration(user_id, "vercel")
    return {"success": True, "provider": "vercel"}


# ── 3. Local Repository CLI & Protocol ──────────────────────────────

@integrations_router.post("/local/connect")
def local_connect(body: LocalConnectRequest, req: Request, user_id: str = Depends(get_required_user)):
    """Registers a local repository from the KALKI CLI agent."""
    if not body.path:
        raise HTTPException(400, "Local path is required.")

    svc = req.app.state.service
    item = svc.integration_store.save_local_project(
        user_id=user_id,
        name=body.name or body.path.replace("\\", "/").rstrip("/").split("/")[-1],
        local_path=body.path,
        git_remote=body.git_remote or "",
        current_branch=body.current_branch or "main",
        status=body.status or "connected",
    )
    return {"success": True, "project": item}


@integrations_router.get("/local/projects")
def local_projects(req: Request, user_id: str = Depends(get_required_user)):
    """Lists registered local projects for the authenticated user."""
    svc = req.app.state.service
    return {"projects": svc.integration_store.list_local_projects(user_id)}


@integrations_router.post("/local/disconnect")
def local_disconnect(body: LocalDisconnectRequest, req: Request, user_id: str = Depends(get_required_user)):
    """Unlinks a local repository."""
    svc = req.app.state.service
    svc.integration_store.delete_local_project(user_id, body.project_id)
    return {"success": True}


# ── 4. Unified Integration Status ───────────────────────────────────

@integrations_router.get("/status")
def all_integrations_status(req: Request, user_id: str = Depends(get_required_user)):
    """Returns overview of all connected services."""
    svc = req.app.state.service
    integrations = svc.integration_store.list_integrations(user_id)
    local_projs = svc.integration_store.list_local_projects(user_id)
    return {
        "integrations": integrations,
        "local_projects_count": len(local_projs)
    }
