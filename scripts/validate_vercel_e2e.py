"""REAL Vercel E2E through KALKI's actual ToolRegistry path (read-only / SAFE).

Path proven:
  KALKI -> register_builtins + register_all_tools -> registry.get('vercel_*')
  -> Tool.invoke(args, ctx) -> real Vercel API.

Only SAFE (non-destructive) operations are exercised: vercel_status + vercel_logs
against an EXISTING deployment. Creating a NEW deployment (vercel_deploy) is an
ELEVATED/DANGEROUS outward action and is handled separately. Never prints token.

Env: KALKI_VERCEL_E2E_DEPLOYMENT must be an existing deployment id.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import _load_dotenv
_load_dotenv()

from agent.tools.base import ToolContext, ToolRegistry
from agent.tools.builtins import register_builtins
from tools import register_all_tools

DEP = os.environ.get("KALKI_VERCEL_E2E_DEPLOYMENT")
if not DEP:
    print("Vercel SAFE E2E: BLOCKED — set KALKI_VERCEL_E2E_DEPLOYMENT to an existing id")
    sys.exit(2)

registry = register_builtins(ToolRegistry())
register_all_tools(registry)
ctx = ToolContext(run_id="vercel-e2e", project="kalki")

print(f"vercel_* tools registered: "
      f"{[n for n in registry.names() if n.startswith('vercel_')]}")
print(f"Target deployment: {DEP}\n")

# 1. Authentication + project/deployment access + verification (vercel_status)
st_tool = registry.get("vercel_status")
r = st_tool.invoke({"deployment_id": DEP}, ctx)
auth_ok = r.ok
print(f"Vercel authentication + project access: {'PASS' if auth_ok else 'FAIL'}"
      + ("" if auth_ok else f" — {r.error}"))
if auth_ok:
    print(f"    -> deployment state={r.output.get('state')} url={r.output.get('url')}")

# 2. Deployment verification via logs (vercel_logs)
lg_tool = registry.get("vercel_logs")
r2 = lg_tool.invoke({"deployment_id": DEP}, ctx)
logs_ok = r2.ok
print(f"Deployment verification (logs read): {'PASS' if logs_ok else 'FAIL'}"
      + ("" if logs_ok else f" — {r2.error}"))
if logs_ok:
    print(f"    -> log entries returned: {r2.output.get('log_count')}")

read_ok = auth_ok and logs_ok
print("\nVercel READ/verify E2E (auth + access + status + verification):",
      "PROVEN" if read_ok else "NOT PROVEN")
sys.exit(0 if read_ok else 1)
