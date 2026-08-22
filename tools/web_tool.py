"""Web / documentation research tool for KALKI.

Provides: ``web_fetch``, ``web_search``.

This is an **engineering research tool** — it fetches documentation and
technical content, not a general-purpose browser.  Uses stdlib urllib
only (zero dependencies).
"""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from agent.tools.base import Tool, ToolContext, ToolRegistry
from shared.contracts import FailureClass, RiskLevel, ToolResult, ToolSpec


def _strip_html(raw: str) -> str:
    """Crude but dependency-free HTML → text conversion."""
    # Remove script/style blocks.
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
    # Remove tags.
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode entities.
    text = html.unescape(text)
    # Collapse whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(raw_html: str) -> str:
    """Pull the <title> from raw HTML."""
    m = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.S | re.I)
    return html.unescape(m.group(1).strip()) if m else ""


# ── web_fetch ────────────────────────────────────────────────────
class WebFetchTool(Tool):
    spec = ToolSpec(
        name="web_fetch",
        description=(
            "Fetch a URL and extract its text content.  Returns title, "
            "source URL, and cleaned text.  Useful for reading documentation."
        ),
        parameters={
            "url": "str — URL to fetch",
            "max_chars": "int (optional, default 10000) — max content length",
            "timeout": "int (optional, default 15) — seconds",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = args.get("url")
        if not url:
            return ToolResult.failure(
                self.spec.name, "missing 'url'", FailureClass.TOOL_ERROR
            )
        timeout = int(args.get("timeout", 15))
        max_chars = int(args.get("max_chars", 10000))

        req = urllib.request.Request(
            url, headers={"User-Agent": "KALKI-Agent/1.0 (engineering research)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return ToolResult.failure(
                self.spec.name, f"HTTP {e.code}: {e.reason}",
                FailureClass.TRANSIENT,
            )
        except (urllib.error.URLError, OSError, ValueError) as e:
            return ToolResult.failure(
                self.spec.name, f"fetch failed: {e}",
                FailureClass.TRANSIENT,
            )

        title = _extract_title(raw)
        content = _strip_html(raw)[:max_chars]

        return ToolResult.success(self.spec.name, output={
            "url": url,
            "title": title,
            "content": content,
            "length": len(content),
        })


# ── web_search ───────────────────────────────────────────────────
class WebSearchTool(Tool):
    spec = ToolSpec(
        name="web_search",
        description=(
            "Search for technical documentation and engineering resources.  "
            "Uses DuckDuckGo Lite (no API key required).  Returns a list of "
            "results with title, URL, and snippet."
        ),
        parameters={
            "query": "str — search query",
            "max_results": "int (optional, default 5)",
        },
        risk=RiskLevel.SAFE,
    )

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = args.get("query")
        if not query:
            return ToolResult.failure(
                self.spec.name, "missing 'query'", FailureClass.TOOL_ERROR
            )
        max_results = int(args.get("max_results", 5))

        encoded = urllib.parse.urlencode({"q": query})
        url = f"https://lite.duckduckgo.com/lite/?{encoded}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "KALKI-Agent/1.0 (engineering research)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError) as e:
            return ToolResult.failure(
                self.spec.name, f"search failed: {e}",
                FailureClass.TRANSIENT,
            )

        # Parse DuckDuckGo Lite results (simple HTML table).
        results = self._parse_ddg_lite(raw, max_results)
        return ToolResult.success(self.spec.name, output=results)

    @staticmethod
    def _parse_ddg_lite(raw_html: str, max_results: int) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        # DuckDuckGo Lite uses <a> tags with class "result-link" or similar.
        # Fallback: extract all <a href="..."> with reasonable URLs.
        links = re.findall(
            r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            raw_html, re.S | re.I,
        )
        seen: set[str] = set()
        for href, title_html in links:
            # Skip DuckDuckGo's own links.
            if "duckduckgo.com" in href:
                continue
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if not title or href in seen:
                continue
            seen.add(href)
            results.append({
                "title": html.unescape(title),
                "url": href,
                "snippet": "",
            })
            if len(results) >= max_results:
                break
        return results


# ── registration ─────────────────────────────────────────────────
def register_web_tools(registry: ToolRegistry) -> None:
    for cls in (WebFetchTool, WebSearchTool):
        registry.register(cls())
