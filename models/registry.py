"""Provider selection with graceful fallback.

Resolution order for a requested provider:
  1. Build the requested provider.
  2. If it is not ``available()`` (missing creds / unreachable), fall back
     through: omniroute -> anthropic -> openai -> mock.
The mock provider is always available, so ``get_provider`` never fails.
"""
from __future__ import annotations

import logging
from typing import Optional

from config.settings import Settings, get_settings
from models.base import ModelProvider
from models.direct import DirectAnthropicProvider, DirectOpenAIProvider
from models.mock import MockProvider
from models.omniroute import OmniRouteProvider
from models.huggingface import HuggingFaceProvider

log = logging.getLogger("kalki.models")


def build_provider(name: str, settings: Settings) -> ModelProvider:
    name = (name or "mock").lower()
    if name == "mock":
        return MockProvider(model=settings.model_name)
    if name == "omniroute":
        return OmniRouteProvider(
            model=settings.model_name,
            base_url=settings.omniroute_base_url,
            api_key=settings.omniroute_api_key,
            health_path=settings.omniroute_health_path,
        )
    if name == "anthropic":
        return DirectAnthropicProvider(
            model=settings.model_name, api_key=settings.anthropic_api_key
        )
    if name == "openai":
        return DirectOpenAIProvider(
            model=settings.model_name, api_key=settings.openai_api_key
        )
    if name == "huggingface":
        return HuggingFaceProvider(
            model=settings.model_name, api_key=settings.huggingface_api_key
        )
    log.warning("Unknown provider %r; using mock.", name)
    return MockProvider(model=settings.model_name)


_FALLBACK_ORDER = ["omniroute", "anthropic", "openai", "huggingface", "mock"]


def get_provider(
    name: Optional[str] = None, settings: Optional[Settings] = None
) -> ModelProvider:
    """Return the best available provider, honouring the requested one first."""
    settings = settings or get_settings()
    requested = (name or settings.model_provider or "mock").lower()

    provider = build_provider(requested, settings)
    if provider.available():
        return provider

    log.warning("Provider %r unavailable; attempting fallbacks.", requested)
    for candidate in _FALLBACK_ORDER:
        if candidate == requested:
            continue
        p = build_provider(candidate, settings)
        if p.available():
            log.warning("Falling back to provider %r.", candidate)
            return p
    # mock is always available; this is defensive.
    return MockProvider(model=settings.model_name)
