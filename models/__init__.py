"""Model provider abstraction for KALKI.

The core agent logic depends ONLY on :class:`ModelProvider`. Concrete
providers (mock, OmniRoute, direct Anthropic/OpenAI/Gemini) are selected at
the edge via :func:`get_provider`. OmniRoute is one optional provider, never
a hard dependency — if it is unstable, KALKI falls back to a direct provider
or the deterministic mock.
"""
from models.base import ModelMessage, ModelProvider, ModelResponse
from models.mock import MockProvider
from models.registry import build_provider, get_provider

__all__ = [
    "ModelMessage",
    "ModelProvider",
    "ModelResponse",
    "MockProvider",
    "build_provider",
    "get_provider",
]
