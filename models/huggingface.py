"""Hugging Face Inference Providers (router) provider.

This provider communicates with Hugging Face's OpenAI-compatible inference
*router* using the standard urllib library (no external SDK required).

Endpoint note: the legacy ``api-inference.huggingface.co`` serverless host has
been retired (it no longer resolves via DNS). The current, verified mechanism
is the Inference Providers router at ``https://router.huggingface.co`` with the
OpenAI-compatible path ``/v1/chat/completions`` — the model name travels in the
JSON payload and the router selects a serving provider. This was confirmed live
against a real model response before the endpoint here was updated.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from models.base import ModelProvider, ModelResponse


class HuggingFaceProvider(ModelProvider):
    name = "huggingface"

    def __init__(
        self, model: str = "meta-llama/Llama-3.1-8B-Instruct", api_key: str = "", timeout: float = 30.0, **kw: Any
    ) -> None:
        super().__init__(model=model, **kw)
        self.api_key = api_key
        self.timeout = timeout
        # HF Inference Providers router — OpenAI-compatible. The model name is
        # supplied in the JSON payload (not the URL); the router routes to a
        # serving provider. Legacy api-inference.huggingface.co is retired.
        self.base_url = "https://router.huggingface.co"

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
        """Reachability probe for Hugging Face."""
        if not self.api_key:
            return False
        # The models endpoint isn't fully supported natively for global reachability, 
        # so we rely on having an API key. We could optionally do a lightweight GET request,
        # but just having the API key configured is a strong enough indicator to try it.
        return True

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ModelResponse:
        if not self.api_key:
            raise RuntimeError("Hugging Face provider unavailable (missing HF_TOKEN).")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        # OpenAI-compatible chat completions on the HF router. The model is
        # carried in the payload above, so the path is fixed.
        path = "/v1/chat/completions"

        try:
            resp = self._post(path, payload)
            text = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ModelResponse(text=text, model=self.model, raw=resp)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"Hugging Face API error {exc.code}: {body}") from exc
