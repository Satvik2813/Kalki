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

import asyncio
import json
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - env dependent
    raise RuntimeError(
        "The API layer needs FastAPI. Install with: pip install 'kalki[api]'"
    ) from exc

from backend.service import KalkiService
from shared.contracts import ExecutionStatus


class CreateTaskRequest(BaseModel):
    objective: str
    project: Optional[str] = None
    autonomy: Optional[str] = None       # supervised | autonomous
    start: bool = False                  # create-and-start convenience


class ApproveRequest(BaseModel):
    tools: list[str] = []


def create_app(service: Optional[KalkiService] = None) -> "FastAPI":
    app = FastAPI(title="KALKI", version="0.1.0",
                  description="Autonomous AI software engineer — core API.")
    svc = service or KalkiService()
    app.state.service = svc

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "kalki", "runs": len(svc.list_runs())}

    @app.post("/api/tasks")
    def create_task(req: CreateTaskRequest):
        state = svc.create(req.objective, project=req.project, autonomy=req.autonomy)
        if req.start:
            svc.start(state.id)
        return state.to_dict()

    @app.get("/api/tasks")
    def list_tasks():
        return {"tasks": [s.to_dict() for s in svc.list_runs()]}

    @app.get("/api/tasks/{run_id}")
    def get_task(run_id: str):
        try:
            return svc.get(run_id).to_dict()
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
    def projects():
        return {"projects": svc.projects()}

    @app.get("/api/memory")
    def memory(limit: int = Query(50)):
        return {"memories": svc.recent_memories(limit=limit)}

    return app


# Module-level app for `uvicorn api.app:app`
try:
    app = create_app()
except Exception:  # pragma: no cover - keeps import cheap when service can't init
    app = None
