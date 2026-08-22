"""FastAPI application exposing the KALKI agent.

Endpoints (contract for Dev 2 — see docs/CONTRACTS.md §API):

    POST /api/tasks                  create a run (objective -> plan-ready)
    GET  /api/tasks                  list runs
    GET  /api/tasks/{id}             run state (status, plan, node)
    POST /api/tasks/{id}/start       begin autonomous execution
    GET  /api/tasks/{id}/events      event history (?after=seq) or SSE (?stream=1)
    POST /api/tasks/{id}/approve     approve gated tools, resume execution
    GET  /api/tasks/{id}/result      terminal ExecutionResult
    GET  /api/projects               known projects
    GET  /api/memory                 recent memory records
    GET  /health                     liveness

Realtime events are available two ways so any frontend works: poll
``/events?after=<seq>`` for JSON, or open ``/events?stream=1`` for Server-Sent
Events. Both replay history, so a late subscriber never misses events.
"""
from __future__ import annotations

import os
import sys

# Ensure project root is in sys.path when running as a Serverless Function on Vercel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import asyncio
import json
from typing import Optional

import os
try:
    from fastapi import FastAPI, HTTPException, Query, Depends, Request
    from fastapi.responses import StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import jwt
except ImportError as exc:  # pragma: no cover - env dependent
    raise RuntimeError(
        "The API layer needs FastAPI. Install with: pip install 'kalki[api]'"
    ) from exc

from backend.service import KalkiService
from shared.contracts import ExecutionStatus
from api.auth import auth_router
from api.integrations import integrations_router


class CreateTaskRequest(BaseModel):
    objective: str
    project: Optional[str] = None
    autonomy: Optional[str] = None       # supervised | autonomous
    start: bool = False                  # create-and-start convenience


class ApproveRequest(BaseModel):
    tools: list[str] = []


def get_current_user(req: Request) -> Optional[str]:
    auth = req.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth.split(" ")[1]
    svc: KalkiService = req.app.state.service
    secret = getattr(svc.settings, "supabase_jwt_secret", "") or getattr(svc.settings, "encryption_key", "")
    if not secret:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        return payload.get("sub")
    except Exception:
        raise HTTPException(401, "Invalid token")

def create_app(service: Optional[KalkiService] = None) -> "FastAPI":
    app = FastAPI(title="KALKI", version="0.1.0",
                  description="Autonomous AI software engineer — core API.")
    svc = service or KalkiService()
    app.state.service = svc

    app.include_router(auth_router)
    app.include_router(integrations_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "kalki", "runs": len(svc.list_runs())}

    @app.post("/api/tasks")
    def create_task(req: CreateTaskRequest, user_id: Optional[str] = Depends(get_current_user)):
        state = svc.create(req.objective, project=req.project, autonomy=req.autonomy, user_id=user_id)
        if req.start:
            svc.start(state.id)
        return state.to_dict()

    @app.get("/api/tasks")
    def list_tasks(user_id: Optional[str] = Depends(get_current_user)):
        return {"tasks": [s.to_dict() for s in svc.list_runs(user_id=user_id)]}

    @app.get("/api/tasks/{run_id}")
    def get_task(run_id: str, user_id: Optional[str] = Depends(get_current_user)):
        try:
            state = svc.get(run_id)
            if state.user_id and state.user_id != user_id:
                raise HTTPException(403, "access denied")
            return state.to_dict()
        except KeyError:
            raise HTTPException(404, "run not found")

    @app.post("/api/tasks/{run_id}/start")
    def start_task(run_id: str):
        try:
            state = svc.start(run_id)
        except KeyError:
            raise HTTPException(404, "run not found")
        return {"run_id": run_id, "status": state.status.value, "started": True}

    @app.post("/api/tasks/{run_id}/approve")
    def approve_task(run_id: str, req: ApproveRequest):
        try:
            state = svc.approve(run_id, req.tools)
        except KeyError:
            raise HTTPException(404, "run not found")
        return {"run_id": run_id, "approved": req.tools, "status": state.status.value}

    @app.get("/api/tasks/{run_id}/result")
    def task_result(run_id: str):
        try:
            return svc.result(run_id)
        except KeyError:
            raise HTTPException(404, "run not found")

    @app.get("/api/tasks/{run_id}/events")
    async def task_events(run_id: str, after: int = Query(0),
                          stream: int = Query(0)):
        try:
            svc.get(run_id)
        except KeyError:
            raise HTTPException(404, "run not found")

        if not stream:
            return {"events": [e.to_dict() for e in svc.events(run_id, after_seq=after)]}

        async def event_gen():
            last = after
            # Replay + live-follow until the run reaches a terminal state.
            while True:
                for e in svc.events(run_id, after_seq=last):
                    last = e.seq
                    yield f"event: {e.type.value}\ndata: {json.dumps(e.to_dict())}\n\n"
                status = svc.status(run_id)
                if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED,
                              ExecutionStatus.BLOCKED, ExecutionStatus.AWAITING_APPROVAL):
                    # flush any final events then close
                    for e in svc.events(run_id, after_seq=last):
                        last = e.seq
                        yield f"event: {e.type.value}\ndata: {json.dumps(e.to_dict())}\n\n"
                    yield f"event: _end\ndata: {json.dumps({'status': status.value})}\n\n"
                    return
                await asyncio.sleep(0.15)

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @app.get("/api/projects")
    def projects(user_id: Optional[str] = Depends(get_current_user)):
        return {"projects": svc.projects(user_id=user_id)}

    @app.get("/api/memory")
    def memory(limit: int = Query(50), user_id: Optional[str] = Depends(get_current_user)):
        return {"memories": svc.recent_memories(limit=limit, user_id=user_id)}

    # Mount static frontend files if directory exists
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if not os.path.exists(frontend_dir):
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
    if os.path.exists(frontend_dir):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


# Module-level app for `uvicorn api.app:app`
app = create_app()
