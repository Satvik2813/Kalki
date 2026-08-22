"""OmniRoute gateway provider.

OmniRoute is an OpenAI-compatible model-routing layer. This provider talks to
it over HTTP using only the stdlib (urllib), so it adds no dependency. It is
strictly optional: the registry will fall back to a direct provider or the
mock if OmniRoute is unreachable. KALKI's core never imports this module —
only the registry does, at the edge.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from models.base import ModelProvider, ModelResponse


class OmniRouteProvider(ModelProvider):
    name = "omniroute"

    def __init__(self, model: str = "claude-sonnet-4", base_url: str = "",
                 api_key: str = "", timeout: float = 30.0,
                 health_path: str = "", **kw: Any) -> None:
        super().__init__(model=model, **kw)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        # Endpoint used by ``available()`` as a reachability probe. OmniRoute
        # has no ``/health``; the OpenAI-compatible ``/v1/models`` route is
        # always served, so it doubles as a liveness probe. Override via
        # OMNIROUTE_HEALTH_PATH if a deployment exposes a dedicated one
        # (e.g. ``/api/monitoring/health``).
        self.health_path = health_path or "/v1/models"

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def available(self) -> bool:
        """A cheap reachability probe — reliability gate before we trust it.

        "Reachable" means the server answered, so any HTTP status < 500 —
        including 401/403 (auth required) or 404 — counts as available: the
        gateway is up, even if this particular probe is unauthorized. Only a
        connection failure, timeout, or 5xx means unavailable. This is what
        lets the registry fall back when OmniRoute is genuinely down without
        wrongly vetoing a running gateway."""
        if not self.base_url:
            return False
        req = urllib.request.Request(f"{self.base_url}{self.health_path}",
                                     method="GET")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(req, timeout=min(self.timeout, 5.0)) as resp:
                return resp.status < 500
        except urllib.error.HTTPError as exc:
            # The server responded with an HTTP error -> it is reachable.
            return exc.code < 500
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        body = self._post("/v1/chat/completions", payload)
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected OmniRoute response: {body!r}") from exc
        return ModelResponse(text=text or "", model=self.model, raw=body)
