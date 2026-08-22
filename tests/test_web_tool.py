"""Tests for web tools (web_fetch, web_search) — mocked, no real HTTP."""
from unittest.mock import patch, MagicMock
import io

from agent.tools.base import ToolContext, ToolRegistry
from shared.contracts import FailureClass
from tools.web_tool import register_web_tools, _strip_html, _extract_title


def _reg() -> ToolRegistry:
    r = ToolRegistry()
    register_web_tools(r)
    return r


def _ctx(tmp_path) -> ToolContext:
    return ToolContext(workspace_root=str(tmp_path), run_id="test-run")


class TestStripHtml:
    def test_removes_tags(self):
        assert "hello world" in _strip_html("<p>hello <b>world</b></p>")

    def test_removes_scripts(self):
        assert "script" not in _strip_html("<script>alert('x')</script>text")

    def test_decodes_entities(self):
        assert "&" in _strip_html("&amp;")


class TestExtractTitle:
    def test_extracts_title(self):
        assert _extract_title("<html><title>My Page</title></html>") == "My Page"

    def test_no_title(self):
        assert _extract_title("<html><body>no title</body></html>") == ""


class TestWebFetch:
    def test_missing_url(self, tmp_path):
        reg = _reg()
        res = reg.get("web_fetch").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_successful_fetch(self, tmp_path):
        html_content = b"<html><title>Docs</title><body><p>Hello World</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = html_content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("tools.web_tool.urllib.request.urlopen", return_value=mock_resp):
            reg = _reg()
            res = reg.get("web_fetch").invoke(
                {"url": "https://docs.example.com"}, _ctx(tmp_path)
            )
        assert res.ok
        assert res.output["title"] == "Docs"
        assert "Hello World" in res.output["content"]

    def test_network_failure(self, tmp_path):
        import urllib.error
        with patch("tools.web_tool.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("timeout")):
            reg = _reg()
            res = reg.get("web_fetch").invoke(
                {"url": "https://unreachable.example.com"}, _ctx(tmp_path)
            )
        assert not res.ok
        assert res.failure_class == FailureClass.TRANSIENT


class TestWebSearch:
    def test_missing_query(self, tmp_path):
        reg = _reg()
        res = reg.get("web_search").invoke({}, _ctx(tmp_path))
        assert not res.ok
        assert res.failure_class == FailureClass.TOOL_ERROR

    def test_successful_search(self, tmp_path):
        fake_html = b"""
        <html><body>
        <a href="https://docs.python.org/3/">Python Docs</a>
        <a href="https://stackoverflow.com/q/123">SO Question</a>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_html
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("tools.web_tool.urllib.request.urlopen", return_value=mock_resp):
            reg = _reg()
            res = reg.get("web_search").invoke(
                {"query": "python docs"}, _ctx(tmp_path)
            )
        assert res.ok
        assert len(res.output) >= 1

    def test_search_network_failure(self, tmp_path):
        import urllib.error
        with patch("tools.web_tool.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("dns error")):
            reg = _reg()
            res = reg.get("web_search").invoke(
                {"query": "test"}, _ctx(tmp_path)
            )
        assert not res.ok
        assert res.failure_class == FailureClass.TRANSIENT
