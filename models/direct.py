"""Direct model providers (Anthropic, OpenAI, Gemini, Mistral).

These provide direct model access with fallback. They import their SDKs lazily
and support standard HTTPS REST fallbacks via stdlib ``urllib`` so the core
never hard-depends on third-party SDK packages.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Optional

from models.base import ModelProvider, ModelResponse

log = logging.getLogger("kalki.models.direct")


# ── OpenAI Provider ──────────────────────────────────────────────────

class DirectOpenAIProvider(ModelProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "", **kw: Any):
        # Resolve to standard OpenAI model if generic
        if not model or "claude" in model or "gemini" in model or "mistral" in model:
            model = "gpt-4o-mini"
        super().__init__(model=model, **kw)
        self.api_key = api_key
        self._client = None

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
            return self._client
        except ImportError:
            return None

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        if not self.api_key:
            raise RuntimeError("OpenAI provider unavailable (missing API key).")

        client = self._client_or_none()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if client is not None:
            resp = client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
            )
            text = resp.choices[0].message.content or ""
            return ModelResponse(text=text, model=self.model, raw=resp)

        # Fallback via REST API (urllib)
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": messages,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"] or ""
            return ModelResponse(text=text, model=self.model, raw=data)


# ── Anthropic Provider ───────────────────────────────────────────────

class DirectAnthropicProvider(ModelProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: str = "", **kw: Any):
        if not model or model == "claude-sonnet-4" or "gpt" in model or "gemini" in model:
            model = "claude-3-5-sonnet-20241022"
        super().__init__(model=model, **kw)
        self.api_key = api_key
        self._client = None

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
            return self._client
        except ImportError:
            return None

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        if not self.api_key:
            raise RuntimeError("Anthropic provider unavailable (missing API key).")

        client = self._client_or_none()
        if client is not None:
            msg = client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 2048),
                temperature=temperature,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(getattr(b, "text", "") for b in msg.content)
            return ModelResponse(text=text, model=self.model, raw=msg)

        # Fallback via REST API (urllib)
        url = "https://api.anthropic.com/v1/messages"
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = "".join(b.get("text", "") for b in data.get("content", []))
            return ModelResponse(text=text, model=self.model, raw=data)


# ── Gemini Provider ──────────────────────────────────────────────────

class DirectGeminiProvider(ModelProvider):
    name = "gemini"

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str = "", **kw: Any):
        if not model or "claude" in model or "gpt" in model:
            model = "gemini-2.0-flash"
        super().__init__(model=model, **kw)
        self.api_key = api_key

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        if not self.api_key:
            raise RuntimeError("Gemini provider unavailable (missing API key).")

        model_clean = self.model.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_clean}:generateContent?key={self.api_key}"

        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
            return ModelResponse(text=text, model=self.model, raw=data)


# ── Mistral Provider ─────────────────────────────────────────────────

class DirectMistralProvider(ModelProvider):
    name = "mistral"

    def __init__(self, model: str = "mistral-small-latest", api_key: str = "", agent_id: str = "", **kw: Any):
        if not model or "claude" in model or "gpt" in model:
            model = "mistral-small-latest"
        super().__init__(model=model, **kw)
        self.api_key = api_key
        self.agent_id = agent_id

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        if not self.api_key:
            raise RuntimeError("Mistral provider unavailable (missing API key).")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # If agent_id is provided and no specific chat model override requested, route through agents endpoint
        if self.agent_id:
            url = "https://api.mistral.ai/v1/agents/completions"
            payload = {
                "agent_id": self.agent_id,
                "messages": messages,
            }
        else:
            url = "https://api.mistral.ai/v1/chat/completions"
            payload = {
                "model": self.model,
                "temperature": temperature,
                "messages": messages,
            }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"] or ""
            return ModelResponse(text=text, model=self.model, raw=data)
