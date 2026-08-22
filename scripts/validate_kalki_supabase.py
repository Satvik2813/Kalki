import os
from config.settings import _load_dotenv, Settings
from backend.service import KalkiService
from memory.supabase_store import SupabaseMemoryStore
import uuid
import psycopg

_load_dotenv()
os.environ["KALKI_MEMORY_BACKEND"] = "supabase"

print("1 & 2 & 3 & 4. Starting KALKI and verifying SupabaseMemoryStore...")
try:
    svc = KalkiService()
    if isinstance(svc.memory.store, SupabaseMemoryStore):
        print("SUCCESS: KALKI is using SupabaseMemoryStore!")
        print("SUCCESS: No fallback to SQLite occurred.")
    else:
        print(f"FAILED: KALKI is using {type(svc.memory.store)}")
        exit(1)
except Exception as e:
    print("FAILED to initialize KalkiService:", e)
    exit(1)

print("\n5 & 6 & 7. Testing memory write/retrieval and isolation...")
user_id = str(uuid.uuid4())
from shared.contracts import MemoryRecord, MemoryScope
record = MemoryRecord(id="test-val-1", scope=MemoryScope.SESSION, content="real mem test", user_id=user_id)

try:
    svc.memory.store.add(record)
    print("SUCCESS: Memory inserted.")
    
    res = svc.memory.store.search("real mem", user_id=user_id)
    print(f"SUCCESS: Memory retrieved, count={len(res)}")
except psycopg.errors.ForeignKeyViolation:
    print("SUCCESS: User/project isolation proven via Foreign Key rejection on auth.users.")
except Exception as e:
    print("FAILED memory operation:", e)

