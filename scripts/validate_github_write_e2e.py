"""SAFE, net-zero GitHub WRITE E2E through KALKI's actual ToolRegistry path.

Proves the ELEVATED branch-creation path:
  KALKI -> registry.get('github_create_branch') -> Tool.invoke -> real GitHub API
  -> branch ref created on the repo -> verified via real API -> ref DELETED again.

The branch carries no commits, no code change, and no PR/merge. It is created
from the repo's default branch tip and removed immediately, leaving the remote
exactly as it was (net-zero). Cleanup delete uses the raw API (KALKI exposes no
delete-branch tool). Never prints the token.
"""
from __future__ import annotations

import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import _load_dotenv
_load_dotenv()

from agent.tools.base import ToolContext, ToolRegistry
from agent.tools.builtins import register_builtins
from tools import register_all_tools

REPO = os.environ.get("KALKI_GH_E2E_REPO", "Satvik2813/Kalki")
BRANCH = f"kalki-e2e-probe-{int(time.time())}"
tok = os.environ.get("GITHUB_TOKEN")

def _raw(method, path):
    req = urllib.request.Request(
        f"https://api.github.com{path}", method=method,
        headers={"Authorization": f"Bearer {tok}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, (json.loads(r.read().decode() or "{}") if method != "DELETE" else {})

registry = register_builtins(ToolRegistry())
register_all_tools(registry)
ctx = ToolContext(run_id="gh-write-e2e", project="kalki")

# Determine the repo's default branch to base the throwaway branch on.
repo_res = registry.get("github_get_repo").invoke({"repo": REPO}, ctx)
base = repo_res.output.get("default_branch") if repo_res.ok else "main"
print(f"Repo: {REPO} | base (default) branch: {base} | new branch: {BRANCH}\n")

# 1) CREATE the branch through KALKI's tool path (ELEVATED).
create = registry.get("github_create_branch").invoke(
    {"repo": REPO, "branch": BRANCH, "from_ref": base}, ctx)
create_ok = create.ok
print(f"Branch creation via github_create_branch: {'PASS' if create_ok else 'FAIL'}"
      + ("" if create_ok else f" — {create.error}"))
if create_ok:
    print(f"    -> {create.output}")

# 2) VERIFY the ref exists on the real remote.
verify_ok = False
if create_ok:
    try:
        st, ref = _raw("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
        verify_ok = (st == 200 and ref.get("ref") == f"refs/heads/{BRANCH}")
        print(f"Branch verified on remote: {'PASS' if verify_ok else 'FAIL'} "
              f"(sha={ref.get('object',{}).get('sha','')[:8]})")
    except urllib.error.HTTPError as e:
        print(f"Branch verified on remote: FAIL — {e.code}")

# 3) CLEANUP: delete the ref so the remote is net-zero.
cleanup_ok = False
if create_ok:
    try:
        st, _ = _raw("DELETE", f"/repos/{REPO}/git/refs/heads/{BRANCH}")
        cleanup_ok = st in (204, 200)
    except urllib.error.HTTPError as e:
        cleanup_ok = (e.code == 204)
    print(f"Branch deleted (net-zero restore): {'PASS' if cleanup_ok else 'FAIL'}")
    # Confirm it is gone.
    gone = False
    try:
        _raw("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    except urllib.error.HTTPError as e:
        gone = (e.code == 404)
    print(f"Post-delete confirmation (404 expected): {'PASS' if gone else 'FAIL'}")

proven = create_ok and verify_ok and cleanup_ok
print("\nGitHub WRITE E2E (branch create via KALKI tool + verify + net-zero delete):",
      "PROVEN" if proven else "NOT PROVEN")
sys.exit(0 if proven else 1)
