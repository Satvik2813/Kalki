"""Deterministic, offline model provider.

MockProvider makes the whole KALKI engine runnable and testable with zero
network access and zero API keys. It is the default provider and the one the
test-suite exercises. It never depends on OmniRoute or any external service.
"""
from __future__ import annotations

from typing import Any, Optional

from models.base import ModelProvider, ModelResponse, _fallback_tasks
from shared.contracts import Plan


class MockProvider(ModelProvider):
    name = "mock"

    def __init__(self, model: str = "mock-1", **kwargs: Any) -> None:
        super().__init__(model=model, **kwargs)

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ModelResponse:
        """Deterministic responses keyed off the prompt intent."""
        p = prompt.lower()
        if "diagnose" in p or "why did" in p:
            text = (
                "The failure looks transient/tooling-related; adjust the "
                "arguments and retry, then re-run the tests."
            )
        elif "summar" in p:
            text = "Objective handled through the KALKI closed-loop engine."
        else:
            # Echo-style deterministic completion.
            text = f"[mock:{self.model}] {prompt.strip()[:200]}"
        return ModelResponse(text=text, model=self.model, usage={"mock": True})

    def plan(self, objective: str, context: str = "") -> Plan:
        # Deterministic heuristic decomposition — the canonical engineering loop.
        return Plan(objective=objective, tasks=_fallback_tasks(objective))
