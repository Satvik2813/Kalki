"""REAL model E2E through KALKI's actual Director path.

Proves: KALKI Orchestrator (Director) -> Planner -> ModelProvider(HuggingFace)
-> real HF router -> real model response -> Director consumes it to build a Plan
-> Director continues execution.

Gated: only runs when a HF token is configured AND the router is reachable.
Never prints the token. Uses a minimal, harmless, deterministic prompt.

Run:  python scripts/validate_model_e2e.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import _load_dotenv

_load_dotenv()

tok = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
if not tok:
    print("REAL MODEL E2E: BLOCKED — no HF token configured")
    sys.exit(2)

from models.huggingface import HuggingFaceProvider

MODEL = os.environ.get("KALKI_HF_E2E_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

# 1) Direct provider probe (single minimal call) ------------------------------
provider = HuggingFaceProvider(model=MODEL, api_key=tok)
print(f"Provider   : {provider.__class__.__name__}")
print(f"Endpoint   : {provider.base_url}/v1/chat/completions")
print(f"Model      : {provider.model}")
try:
    r = provider.complete("Reply with exactly: KALKI_HF_REAL_OK",
                          temperature=0.0, max_tokens=12)
except Exception as exc:  # noqa: BLE001
    print(f"REAL MODEL E2E: BLOCKED — provider.complete failed: "
          f"{type(exc).__name__}: {exc}")
    sys.exit(1)
print(f"ModelProvider response: {r.text.strip()!r}")

# 2) Full Director path -------------------------------------------------------
# Force the huggingface provider + this model through the normal registry.
os.environ["KALKI_MODEL_PROVIDER"] = "huggingface"
os.environ["KALKI_MODEL_NAME"] = MODEL
# Keep memory offline/local so this test depends only on the model + internet.
os.environ["KALKI_MEMORY_BACKEND"] = "local"
from config.settings import get_settings
get_settings.cache_clear()

from agent.orchestrator import Orchestrator
from models.registry import get_provider
from shared.contracts import ExecutionStatus

settings = get_settings()
resolved = get_provider(settings=settings)
print(f"\nDirector resolved provider: {resolved.name} (model={resolved.model})")
if resolved.name != "huggingface":
    print("REAL MODEL E2E: BLOCKED — registry did not resolve the HF provider "
          f"(got {resolved.name!r}); a real HF response was NOT used by the Director")
    sys.exit(1)

orch = Orchestrator(settings=settings)

captured = {}
_orig_plan = orch.provider.plan

def _traced_plan(objective, context=""):
    plan = _orig_plan(objective, context=context)
    captured["called"] = True
    captured["ntasks"] = len(plan.tasks)
    return plan

orch.provider.plan = _traced_plan  # type: ignore[assignment]

state, result = orch.run(
    objective="Print a short greeting message to the console.",
    project="kalki-e2e-modelcheck",
)

print("\n--- Director run ---")
print(f"Provider.plan invoked (real model call): {captured.get('called', False)}")
print(f"Plan tasks produced by real model      : {captured.get('ntasks')}")
print(f"Director terminal status               : {result.status.value}")
print(f"Director advanced past CREATE_PLAN      : {state.plan is not None}")

model_used = captured.get("called") and resolved.name == "huggingface"
director_consumed = state.plan is not None and captured.get("ntasks", 0) > 0
if model_used and director_consumed:
    print("\nREAL MODEL E2E: PROVEN")
    sys.exit(0)
print("\nREAL MODEL E2E: BLOCKED — path did not complete as required")
sys.exit(1)
