"""Unit tests for ModelProvider registry and direct providers (OpenAI, Anthropic, Gemini, Mistral, Mock)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from config.settings import Settings
from models.base import ModelResponse, _extract_json, _parse_tasks
from models.direct import (
    DirectAnthropicProvider,
    DirectGeminiProvider,
    DirectMistralProvider,
    DirectOpenAIProvider,
)
from models.mock import MockProvider
from models.registry import build_provider, get_provider


# ── 1. Plan Extraction & Tolerant Parsing ───────────────────────────

def test_extract_json_clean():
    raw = '{"tasks": [{"description": "Write tests", "tool": "run_tests"}]}'
    parsed = _extract_json(raw)
    assert parsed == {"tasks": [{"description": "Write tests", "tool": "run_tests"}]}


def test_extract_json_surrounded_by_markdown():
    raw = 'Here is the plan:\n```json\n{"tasks": [{"description": "Test task"}]}\n```\nHope this helps!'
    parsed = _extract_json(raw)
    assert parsed == {"tasks": [{"description": "Test task"}]}


def test_parse_tasks_fallback():
    tasks = _parse_tasks("This is not valid json")
    assert tasks == []


# ── 2. Mock Provider ────────────────────────────────────────────────

def test_mock_provider():
    p = MockProvider()
    assert p.available() is True
    resp = p.complete("Hello")
    assert isinstance(resp, ModelResponse)
    plan = p.plan("Build a feature")
    assert len(plan.tasks) > 0


# ── 3. Direct OpenAI Provider ───────────────────────────────────────

def test_openai_provider_mocked():
    p = DirectOpenAIProvider(model="gpt-4o-mini", api_key="dummy-key")
    assert p.available() is True

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "OpenAI completion response"}}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        # Force REST fallback path
        p._client = None
        with patch.object(p, "_client_or_none", return_value=None):
            resp = p.complete("Hello OpenAI")
            assert resp.text == "OpenAI completion response"


# ── 4. Direct Anthropic Provider ────────────────────────────────────

def test_anthropic_provider_mocked():
    p = DirectAnthropicProvider(model="claude-3-5-sonnet-20241022", api_key="dummy-key")
    assert p.available() is True

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "content": [{"text": "Anthropic response"}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        with patch.object(p, "_client_or_none", return_value=None):
            resp = p.complete("Hello Claude")
            assert resp.text == "Anthropic response"


# ── 5. Direct Gemini Provider ───────────────────────────────────────

def test_gemini_provider_mocked():
    p = DirectGeminiProvider(model="gemini-2.0-flash", api_key="dummy-key")
    assert p.available() is True

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "Gemini response"}]}
            }]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        resp = p.complete("Hello Gemini")
        assert resp.text == "Gemini response"


# ── 6. Direct Mistral Provider ──────────────────────────────────────

def test_mistral_provider_mocked():
    p = DirectMistralProvider(model="mistral-small-latest", api_key="dummy-key")
    assert p.available() is True

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Mistral response"}}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        resp = p.complete("Hello Mistral")
        assert resp.text == "Mistral response"


def test_mistral_agent_provider_mocked():
    p = DirectMistralProvider(model="mistral-small-latest", api_key="dummy-key", agent_id="agent-123")
    assert p.available() is True

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Mistral Agent response"}}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        resp = p.complete("Hello Agent")
        assert resp.text == "Mistral Agent response"


# ── 7. Registry & Fallback Order ────────────────────────────────────

def test_provider_fallback_to_mock_when_no_keys():
    empty_settings = Settings(
        model_provider="anthropic",
        anthropic_api_key="",
        openai_api_key="",
        gemini_api_key="",
        mistral_api_key="",
        huggingface_api_key="",
    )
    provider = get_provider("anthropic", empty_settings)
    assert isinstance(provider, MockProvider)


def test_provider_selection_when_key_present():
    settings = Settings(
        model_provider="mistral",
        mistral_api_key="valid-key",
    )
    provider = get_provider("mistral", settings)
    assert isinstance(provider, DirectMistralProvider)
