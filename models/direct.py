"""Direct model providers (Anthropic / OpenAI).

These are the fallback path when OmniRoute is not used or unstable. They import
their SDKs lazily so the core never requires them; ``available()`` reports
False when the SDK or API key is missing, letting the registry fall back.
"""
from __future__ import annotations

from typing import Any, Optional

from models.base import ModelProvider, ModelResponse


class DirectAnthropicProvider(ModelProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4", api_key: str = "", **kw: Any):
        super().__init__(model=model, **kw)
        self.api_key = api_key
        self._client = None

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import anthropic  # type: ignore
        except ImportError:
            return None
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def available(self) -> bool:
        return self._client_or_none() is not None

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        client = self._client_or_none()
        if client is None:
            raise RuntimeError("Anthropic provider unavailable (missing SDK or API key).")
        msg = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 2048),
            temperature=temperature,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content)
        return ModelResponse(text=text, model=self.model, raw=msg)


class DirectOpenAIProvider(ModelProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "", **kw: Any):
        super().__init__(model=model, **kw)
        self.api_key = api_key
        self._client = None

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import openai  # type: ignore
        except ImportError:
            return None
        self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def available(self) -> bool:
        return self._client_or_none() is not None

    def complete(self, prompt: str, *, system: Optional[str] = None,
                 temperature: float = 0.2, **kwargs: Any) -> ModelResponse:
        client = self._client_or_none()
        if client is None:
            raise RuntimeError("OpenAI provider unavailable (missing SDK or API key).")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=self.model, temperature=temperature, messages=messages,
        )
        return ModelResponse(text=resp.choices[0].message.content or "",
                             model=self.model, raw=resp)
