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
                 api_key: str = "", timeout: float = 30.0, **kw: Any) -> None:
        super().__init__(model=model, **kw)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

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
        """A cheap reachability probe — reliability gate before we trust it."""
        if not self.base_url:
            return False
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return 200 <= resp.status < 500
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
