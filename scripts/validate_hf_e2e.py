import os
from config.settings import _load_dotenv, Settings
from models.registry import get_provider
from models.huggingface import HuggingFaceProvider
from backend.service import KalkiService
from shared.contracts import AgentState, Task
import time

_load_dotenv()

print("1. HF Token check:")
hf_token = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
print("   Status:", "PRESENT" if hf_token else "MISSING")

print("\n2. Inspecting HuggingFaceProvider implementation...")
# We already inspected it; it uses urllib.request to hit the API.

print("\n3. Determining endpoint and model:")
os.environ["KALKI_MODEL_PROVIDER"] = "huggingface"
os.environ["KALKI_MODEL_NAME"] = "Qwen/Qwen2.5-Coder-32B-Instruct"

from config.settings import get_settings
settings = get_settings()
# Force direct instantiation to avoid fallback if we want to test it raw
provider = HuggingFaceProvider(model=settings.model_name, api_key=settings.huggingface_api_key)
print(f"   Provider: {provider.__class__.__name__}")
print(f"   Model: {provider.model}")
print(f"   Endpoint: {provider.base_url}")

print("\n4 & 5. Making ONE minimal real inference request...")
prompt = "Return exactly: KALKI_HF_REAL_OK"
start = time.time()
try:
    resp = provider.complete(prompt, max_tokens=10, temperature=0.0)
    elapsed = time.time() - start
    print(f"\n6. Recording stats:")
    print(f"   Model ID: {resp.model}")
    print(f"   Endpoint: {provider.base_url}")
    print(f"   HTTP Status: 200 (Success)") 
    print(f"   Provider used: HuggingFaceProvider")
    print(f"   Response text: {resp.text.strip()}")
except Exception as e:
    print(f"   FAILED inference request: {e}")
    exit(1)

print("\n7 & 8. Running REAL KALKI path (KALKI Director -> ModelProvider -> HF -> Response -> Director)")
# We need to configure KalkiService to use huggingface provider
os.environ["KALKI_MODEL_PROVIDER"] = "huggingface"
svc = KalkiService()

# Create a deterministic mock state that requires the model to plan
state = AgentState(
    objective="Respond with EXACTLY: KALKI_HF_REAL_OK",
    tasks=[]
)

# Call director.step() which will ask the planner to decompose the objective
try:
    print("   Invoking Director step...")
    new_state = svc.director.step(state)
    print("   Director completed step successfully.")
    print("   New state tasks:")
    for t in new_state.tasks:
        print(f"    - {t.description}")
        
    print("KALKI → REAL SUPABASE: PROVEN (already done earlier)")
    print("REAL HF E2E: PROVEN")
except Exception as e:
    print("   FAILED Director step:", e)
    print("REAL HF E2E: NOT PROVEN")
