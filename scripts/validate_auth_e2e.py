"""REAL authentication E2E through KALKI's FastAPI + JWT + user-scoped memory.

Proves the strongest currently-supported flow:
  login JWT (signed with the REAL supabase_jwt_secret)
  -> FastAPI get_current_user validates it
  -> authenticated user_id (sub)
  -> authenticated task creation scoped to that user
  -> user-scoped memory retrieval
  -> cross-user isolation

Google Auth is intentionally DEFERRED and not exercised.

Safety: uses two DEDICATED throwaway test users and a TEMP local sqlite db, mock
model provider, no network. Does NOT create/modify real Supabase user rows.
Never prints the JWT secret or tokens.
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import _load_dotenv, Settings
_load_dotenv()

import jwt as pyjwt
from fastapi.testclient import TestClient

secret = os.environ.get("SUPABASE_JWT_SECRET", "")
if not secret:
    print("AUTHENTICATION E2E: BLOCKED — SUPABASE_JWT_SECRET not configured")
    sys.exit(2)

from backend.service import KalkiService
from api.app import create_app

USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())

def mint(sub: str) -> str:
    return pyjwt.encode({"sub": sub, "aud": "authenticated"}, secret, algorithm="HS256")

tmp = Path(tempfile.mkdtemp(prefix="kalki_auth_e2e_")) / "auth_e2e.sqlite3"
settings = Settings(
    model_provider="mock", memory_backend="local",
    local_db_path=str(tmp), supabase_jwt_secret=secret, autonomy="supervised",
)
svc = KalkiService(settings=settings)
app = create_app(svc)
client = TestClient(app)

results: dict[str, bool] = {}

# 1. JWT validation -----------------------------------------------------------
#    invalid token -> 401 ; missing header -> unauthenticated (None user)
bad = client.get("/api/tasks", headers={"Authorization": "Bearer not.a.jwt"})
good_hdr_A = {"Authorization": f"Bearer {mint(USER_A)}"}
good_hdr_B = {"Authorization": f"Bearer {mint(USER_B)}"}
ok_list = client.get("/api/tasks", headers=good_hdr_A)
results["JWT validation"] = (bad.status_code == 401 and ok_list.status_code == 200)

# 2. User identification ------------------------------------------------------
#    A valid token's `sub` must become the authenticated user_id on a new task.
created = client.post("/api/tasks", json={"objective": "auth check A"}, headers=good_hdr_A)
task_A = created.json()
results["User identification"] = (created.status_code == 200
                                  and task_A.get("user_id") == USER_A)

# 3. Authenticated task -------------------------------------------------------
#    The created run is listed for A (owned) and NOT listed for B.
list_A = client.get("/api/tasks", headers=good_hdr_A).json()["tasks"]
list_B = client.get("/api/tasks", headers=good_hdr_B).json()["tasks"]
a_ids = {t["id"] for t in list_A}
b_ids = {t["id"] for t in list_B}
results["Authenticated task"] = (task_A["id"] in a_ids and task_A["id"] not in b_ids)

# 4. User-scoped memory -------------------------------------------------------
#    Record a memory for A; A recalls it, B cannot see it.
svc.memory.record_experience("KALKI secret note for user A", user_id=USER_A,
                             tags=["e2e"], objective="auth check A")
mem_A = svc.recent_memories(limit=50, user_id=USER_A)
mem_B = svc.recent_memories(limit=50, user_id=USER_B)
a_has = any("secret note for user A" in m["content"] for m in mem_A)
b_has = any("secret note for user A" in m["content"] for m in mem_B)
results["User-scoped memory"] = (a_has and not b_has)

# 5. Cross-user isolation -----------------------------------------------------
#    B requesting A's task by id -> 403 forbidden.
forbidden = client.get(f"/api/tasks/{task_A['id']}", headers=good_hdr_B)
owner_ok = client.get(f"/api/tasks/{task_A['id']}", headers=good_hdr_A)
results["Cross-user isolation"] = (forbidden.status_code == 403
                                   and owner_ok.status_code == 200)

print("Two dedicated test users (UUIDs) minted with the real JWT secret.\n")
for k, v in results.items():
    print(f"{k}: {'PASS' if v else 'FAIL'}")
print("Google Auth: DEFERRED")

sys.exit(0 if all(results.values()) else 1)
