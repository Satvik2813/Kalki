"""OmniRoute provider: request build, response mapping, reachability,
failure handling, and fallback — all deterministic (no network).

A real end-to-end test against a live OmniRoute server is gated behind
OMNIROUTE_INTEGRATION=1 so normal CI never depends on an external service.
"""
from __future__ import annotations

import io
import json
import os
import urllib.error

import pytest

from config.settings import Settings
from models.mock import MockProvider
from models.omniroute import OmniRouteProvider
from models.registry import get_provider


# ── helpers ───────────────────────────────────────────────────
class _FakeResp:
    def __init__(self, status=200, body=b"{}"):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _openai_body(text: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": text}}]}).encode()


# ── T1: mock still works ──────────────────────────────────────
def test_mock_provider_still_works():
    s = Settings(model_provider="mock")
    p = get_provider(settings=s)
    assert p.name == "mock"
    assert p.complete("hello").text.startswith("[mock:")


# ── T2: correct request build ─────────────────────────────────
def test_builds_openai_compatible_request(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode())
        captured["auth"] = req.get_header("Authorization")
        return _FakeResp(200, _openai_body("ok"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    p = OmniRouteProvider(model="auto", base_url="http://localhost:20128",
                          api_key="k-123")
    p.complete("Hi", system="be terse", temperature=0.0)

    assert captured["url"] == "http://localhost:20128/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["body"]["model"] == "auto"
    assert captured["body"]["messages"][0] == {"role": "system", "content": "be terse"}
    assert captured["body"]["messages"][-1] == {"role": "user", "content": "Hi"}
    assert captured["auth"] == "Bearer k-123"


# ── T3: response mapping ──────────────────────────────────────
def test_maps_openai_response_to_model_response(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=None: _FakeResp(200, _openai_body("KALKI_OK")))
    p = OmniRouteProvider(model="auto", base_url="http://localhost:20128")
    resp = p.complete("say it")
    assert resp.text == "KALKI_OK"
    assert resp.model == "auto"


def test_malformed_response_raises_runtimeerror(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=None: _FakeResp(200, b'{"nope": true}'))
    p = OmniRouteProvider(model="auto", base_url="http://localhost:20128")
    with pytest.raises(RuntimeError):
        p.complete("x")


# ── T4: reachability / failure handling ───────────────────────
def test_available_true_when_server_answers(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=None: _FakeResp(200, b"{}"))
    p = OmniRouteProvider(base_url="http://localhost:20128")
    assert p.available() is True


def test_available_true_on_401_since_server_is_up(monkeypatch):
    def raise_401(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))
    monkeypatch.setattr("urllib.request.urlopen", raise_401)
    p = OmniRouteProvider(base_url="http://localhost:20128")
    assert p.available() is True  # reachable, just unauthorized


def test_available_false_on_connection_error(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr("urllib.request.urlopen", boom)
    p = OmniRouteProvider(base_url="http://localhost:9")
    assert p.available() is False


def test_available_false_on_5xx(monkeypatch):
    def raise_503(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 503, "unavailable", {}, io.BytesIO(b""))
    monkeypatch.setattr("urllib.request.urlopen", raise_503)
    p = OmniRouteProvider(base_url="http://localhost:20128")
    assert p.available() is False


def test_health_path_is_configurable(monkeypatch):
    seen = {}
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout=None: seen.update(url=req.full_url) or _FakeResp(200))
    p = OmniRouteProvider(base_url="http://localhost:20128",
                          health_path="/api/monitoring/health")
    p.available()
    assert seen["url"] == "http://localhost:20128/api/monitoring/health"


# ── T5: fallback when OmniRoute is unavailable ────────────────
def test_registry_falls_back_when_omniroute_unreachable(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("down")
    monkeypatch.setattr("urllib.request.urlopen", boom)
    s = Settings(model_provider="omniroute", omniroute_base_url="http://localhost:9",
                 anthropic_api_key="", openai_api_key="")
    p = get_provider(settings=s)
    assert p.name == "mock"  # fell back through the chain to the always-available mock


# ── T6: autonomous loop still works on mock ───────────────────
def test_planner_still_produces_plan_on_mock():
    plan = MockProvider().plan("Fix the authentication bug and deploy it")
    assert plan.tasks and any(t.tool == "deploy" for t in plan.tasks)


# ── Real integration (opt-in only) ────────────────────────────
@pytest.mark.skipif(os.environ.get("OMNIROUTE_INTEGRATION") != "1",
                    reason="set OMNIROUTE_INTEGRATION=1 to hit a live OmniRoute server")
def test_real_omniroute_end_to_end():
    base = os.environ.get("OMNIROUTE_BASE_URL", "http://localhost:20128")
    model = os.environ.get("KALKI_MODEL_NAME", "auto")
    p = OmniRouteProvider(model=model, base_url=base,
                          api_key=os.environ.get("OMNIROUTE_API_KEY", ""))
    assert p.available(), f"OmniRoute not reachable at {base}"
    resp = p.complete("Return exactly: KALKI_OMNIROUTE_OK")
    assert resp.text and "KALKI_OMNIROUTE_OK" in resp.text
