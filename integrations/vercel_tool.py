"""Vercel deployment integration for KALKI.

Provides: ``vercel_deploy``, ``vercel_status``, ``vercel_logs``,
``vercel_redeploy``.

Auth via ``VERCEL_TOKEN`` env var.  Tokens are NEVER exposed in
ToolResult output.  Uses stdlib ``urllib`` — zero dependencies.

Production deploys are DANGEROUS risk (require approval).
Preview deploys are ELEVATED risk.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec

_API = "https://api.vercel.com"


def _token() -> str | None:
    return os.environ.get("VERCEL_TOKEN")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _vercel_call(method: str, path: str, token: str,
                 body: dict | None = None, timeout: int = 30) -> dict[str, Any]:
    url = f"{_API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(token), method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _no_token(tool: str) -> ToolResult:
    return ToolResult.failure(
        tool, "VERCEL_TOKEN not set — configure it in environment",
        FailureClass.PERMISSION,
    )


# ── vercel_deploy ────────────────────────────────────────────────
class VercelDeployTool(Tool):
    spec = ToolSpec(
        name="vercel_deploy",
        description=(
            "Trigger a Vercel deployment.  Defaults to preview deployment "
            "(ELEVATED risk).  Production target requires DANGEROUS approval."
        ),
        parameters={
            "project": "str (optional) — Vercel project name or ID",
            "target": "str (optional, default 'preview') — 'preview' or 'production'",
            "ref": "str (optional) — git ref to deploy",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)

        target = args.get("target", "preview")
        project = args.get("project", ctx.project or "kalki")

        body: dict[str, Any] = {
            "name": project,
            "target": target,
        }
        ref = args.get("ref")
        if ref:
            body["gitSource"] = {"ref": ref}

        try:
            data = _vercel_call("POST", "/v13/deployments", token, body=body)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name,
                f"Vercel deploy failed: {e.code} {e.reason}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel unreachable: {e}",
                FailureClass.TRANSIENT,
            )

        deploy_url = data.get("url", "")
        if deploy_url and not deploy_url.startswith("http"):
            deploy_url = f"https://{deploy_url}"

        return ToolResult.success(self.spec.name, output={
            "id": data.get("id"),
            "url": deploy_url,
            "target": target,
            "state": data.get("readyState", data.get("state", "QUEUED")),
        }, deploy_url=deploy_url)


# ── vercel_status ────────────────────────────────────────────────
class VercelStatusTool(Tool):
    spec = ToolSpec(
        name="vercel_status",
        description="Check the status of a Vercel deployment.",
        parameters={"deployment_id": "str — Vercel deployment ID"},
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        dep_id = args.get("deployment_id")
        if not dep_id:
            return ToolResult.failure(
                self.spec.name, "missing 'deployment_id'", FailureClass.TOOL_ERROR
            )
        try:
            data = _vercel_call("GET", f"/v13/deployments/{dep_id}", token)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel unreachable: {e}",
                FailureClass.TRANSIENT,
            )

        state = data.get("readyState", data.get("state", "UNKNOWN"))
        return ToolResult.success(self.spec.name, output={
            "id": data.get("id"),
            "state": state,
            "url": data.get("url"),
            "created_at": data.get("createdAt"),
        })


# ── vercel_logs ──────────────────────────────────────────────────
class VercelLogsTool(Tool):
    spec = ToolSpec(
        name="vercel_logs",
        description="Fetch deployment logs from Vercel.",
        parameters={
            "deployment_id": "str — Vercel deployment ID",
            "follow": "bool (optional, default false)",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        dep_id = args.get("deployment_id")
        if not dep_id:
            return ToolResult.failure(
                self.spec.name, "missing 'deployment_id'", FailureClass.TOOL_ERROR
            )
        try:
            data = _vercel_call(
                "GET", f"/v2/deployments/{dep_id}/events", token
            )
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel unreachable: {e}",
                FailureClass.TRANSIENT,
            )

        # data is typically a list of log entries.
        logs = data if isinstance(data, list) else data.get("events", [])
        return ToolResult.success(self.spec.name, output={
            "deployment_id": dep_id,
            "log_count": len(logs),
            "logs": logs[-100:],  # last 100 entries
        })


# ── vercel_redeploy ─────────────────────────────────────────────
class VercelRedeployTool(Tool):
    spec = ToolSpec(
        name="vercel_redeploy",
        description="Redeploy an existing Vercel deployment.",
        parameters={
            "deployment_id": "str — Vercel deployment ID to redeploy",
            "target": "str (optional, default 'preview')",
        },
        risk=RiskLevel.ELEVATED,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        dep_id = args.get("deployment_id")
        if not dep_id:
            return ToolResult.failure(
                self.spec.name, "missing 'deployment_id'", FailureClass.TOOL_ERROR
            )
        target = args.get("target", "preview")
        try:
            data = _vercel_call(
                "POST", f"/v13/deployments?forceNew=1",
                token,
                body={"deploymentId": dep_id, "target": target},
            )
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel redeploy failed: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel unreachable: {e}",
                FailureClass.TRANSIENT,
            )

        deploy_url = data.get("url", "")
        if deploy_url and not deploy_url.startswith("http"):
            deploy_url = f"https://{deploy_url}"

        return ToolResult.success(self.spec.name, output={
            "id": data.get("id"),
            "url": deploy_url,
            "state": data.get("readyState", "QUEUED"),
        }, deploy_url=deploy_url)


# ── vercel_list_projects ─────────────────────────────────────────
class VercelListProjectsTool(Tool):
    spec = ToolSpec(
        name="vercel_list_projects",
        description="List Vercel projects accessible to the token.",
        parameters={
            "limit": "int (optional, default 20) — number of projects to return",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = _token()
        if not token:
            return _no_token(self.spec.name)
        
        limit = int(args.get("limit", 20))
        try:
            data = _vercel_call("GET", f"/v9/projects?limit={limit}", token)
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel API error: {e.code}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"Vercel unreachable: {e}",
                FailureClass.TRANSIENT,
            )
            
        projects = []
        for p in data.get("projects", []):
            projects.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "framework": p.get("framework"),
            })
            
        return ToolResult.success(self.spec.name, output=projects)


# ── registration ─────────────────────────────────────────────────
def register_vercel_tools(registry: ToolRegistry) -> None:
    for cls in (VercelDeployTool, VercelStatusTool, VercelLogsTool, VercelRedeployTool, VercelListProjectsTool):
        registry.register(cls())
