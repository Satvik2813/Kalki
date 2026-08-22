"""REAL GitHub E2E through KALKI's actual ToolRegistry path (read-only / SAFE).

Path proven:
  KALKI -> register_builtins + register_all_tools (the real registry KalkiService
  builds) -> registry.get('github_*') -> Tool.invoke(args, ctx) -> real GitHub API.

Only SAFE (non-destructive, read) operations are exercised here. Branch/commit/PR
are ELEVATED writes and are handled separately (they require a safe scratch repo).
Never prints the token.
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

REPO = os.environ.get("KALKI_GH_E2E_REPO", "Satvik2813/Kalki")

# Build the registry EXACTLY as KalkiService does.
registry = register_builtins(ToolRegistry())
register_all_tools(registry)

ctx = ToolContext(run_id="gh-e2e", project="kalki")

def stage(label, tool_name, args):
    tool = registry.get(tool_name)
    if tool is None:
        print(f"{label}: FAIL — tool {tool_name!r} not in registry")
        return None
    res = tool.invoke(args, ctx)
    ok = res.ok
    print(f"{label}: {'PASS' if ok else 'FAIL'}  ({tool_name})"
          + ("" if ok else f" — {res.error}"))
    return res if ok else None

print(f"Target repo: {REPO}")
print(f"github_* tools registered: "
      f"{[n for n in registry.names() if n.startswith('github_')]}\n")

# 1. Authentication + repo access (github_get_repo)
r = stage("GitHub authentication + repository access", "github_get_repo", {"repo": REPO})
if r:
    print(f"    -> full_name={r.output.get('full_name')} "
          f"default_branch={r.output.get('default_branch')} "
          f"private={r.output.get('private')}")

# 2. Repository inspection (list files + read a file)
r2 = stage("Repository inspection (list files)", "github_list_files", {"repo": REPO, "path": ""})
if r2:
    names = [e["name"] for e in (r2.output or [])][:8]
    print(f"    -> top-level entries (sample): {names}")

r3 = stage("Repository inspection (read file)", "github_get_file",
           {"repo": REPO, "path": "README.md"})
if r3:
    print(f"    -> README.md size={r3.output.get('size')} bytes, "
          f"sha={str(r3.output.get('sha'))[:8]}")

# 3. CI/CD status read (github_actions_status)
r4 = stage("CI/CD status read", "github_actions_status", {"repo": REPO})
if r4 is not None:
    print(f"    -> workflow runs returned: {len(r4.output or [])}")

read_ok = all(x is not None for x in (r, r2, r3)) and r4 is not None
print("\nGitHub READ E2E (auth + access + inspection + tool exec):",
      "PROVEN" if read_ok else "NOT PROVEN")
sys.exit(0 if read_ok else 1)
