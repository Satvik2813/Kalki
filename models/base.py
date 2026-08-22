"""Base model-provider interface.

A provider only has to implement :meth:`ModelProvider.complete`. Higher-level
helpers (:meth:`plan`, :meth:`decide`) are built on top of ``complete`` here
so every provider gets planning/decision behaviour for free; providers may
override them for smarter or deterministic behaviour (see MockProvider).
"""
from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from shared.contracts import Plan, Task, new_id


@dataclass
class ModelMessage:
    role: str            # "system" | "user" | "assistant"
    content: str


@dataclass
class ModelResponse:
    text: str
    model: str = ""
    raw: Any = None
    usage: dict[str, Any] = field(default_factory=dict)


class ModelProvider(abc.ABC):
    """Uniform interface over any LLM backend."""

    name: str = "base"

    def __init__(self, model: str = "", **kwargs: Any) -> None:
        self.model = model
        self.options = kwargs

    # -- the single required primitive ---------------------------
    @abc.abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ModelResponse:
        """Return a completion for ``prompt``."""

    # -- convenience ---------------------------------------------
    def available(self) -> bool:
        """Whether this provider is usable right now (creds/reachable)."""
        return True

    # -- higher-level helpers (override for smarter behaviour) ----
    def plan(self, objective: str, context: str = "") -> Plan:
        """Decompose an objective into a structured :class:`Plan`.

        Default implementation asks the model for JSON and parses it. Providers
        with no reliable JSON mode should override (see MockProvider)."""
        system = (
            "You are KALKI's planning engine. Decompose the engineering "
            "objective into an ordered list of concrete, verifiable tasks. "
            'Respond ONLY with JSON: {"tasks": [{"description": str, '
            '"tool": str|null}]}. Keep tasks small and testable.'
        )
        prompt = f"OBJECTIVE:\n{objective}\n\nCONTEXT:\n{context or '(none)'}"
        resp = self.complete(prompt, system=system, temperature=0.0)
        tasks = _parse_tasks(resp.text)
        if not tasks:
            tasks = _fallback_tasks(objective)
        return Plan(objective=objective, tasks=tasks)

    def decide(self, question: str, context: str = "") -> str:
        resp = self.complete(question, system=context or None, temperature=0.0)
        return resp.text.strip()


# ─────────────────────────────────────────────────────────────
# Parsing helpers shared by providers
# ─────────────────────────────────────────────────────────────
def _parse_tasks(text: str) -> list[Task]:
    """Extract a task list from a model response (tolerant of prose around
    the JSON block)."""
    payload = _extract_json(text)
    if not isinstance(payload, dict):
        return []
    raw_tasks = payload.get("tasks", [])
    tasks: list[Task] = []
    prev_id: Optional[str] = None
    for i, rt in enumerate(raw_tasks, start=1):
        if isinstance(rt, str):
            desc, tool = rt, None
        elif isinstance(rt, dict):
            desc = rt.get("description") or rt.get("task") or ""
            tool = rt.get("tool")
        else:
            continue
        if not desc:
            continue
        tid = f"task-{i}"
        deps = [prev_id] if prev_id else []
        tasks.append(Task(id=tid, description=desc, tool=tool, depends_on=deps))
        prev_id = tid
    return tasks


def _extract_json(text: str) -> Any:
    text = text.strip()
    # strip ```json fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _fallback_tasks(objective: str) -> list[Task]:
    """Deterministic decomposition used when the model returns nothing
    parseable. Encodes the canonical KALKI engineering loop, with safe default
    tool arguments so the plan is runnable against the built-in toolbelt."""
    lower = objective.lower()
    steps: list[tuple[str, Optional[str], dict]] = [
        ("Inspect the repository structure and identify relevant files",
         "list_dir", {"path": "."}),
    ]
    if any(k in lower for k in ("bug", "fix", "error", "broken", "fail")):
        steps.append(("Locate and reproduce the reported failure", "run_tests", {}))
        steps.append(("Apply a code change to address the root cause",
                      "write_file",
                      {"path": ".kalki/patch_notes.md",
                       "content": f"# KALKI patch notes\nObjective: {objective}\n"}))
    else:
        steps.append(("Implement the requested change", "write_file",
                      {"path": ".kalki/change_notes.md",
                       "content": f"# KALKI change notes\nObjective: {objective}\n"}))
    steps.append(("Run the test suite to validate the change", "run_tests", {}))
    if any(k in lower for k in ("deploy", "ship", "release")):
        steps.append(("Deploy the change to a preview environment", "deploy",
                      {"environment": "preview"}))
    tasks: list[Task] = []
    prev: Optional[str] = None
    for i, (desc, tool, args) in enumerate(steps, start=1):
        tid = f"task-{i}"
        tasks.append(Task(id=tid, description=desc, tool=tool, tool_args=args,
                          depends_on=[prev] if prev else []))
        prev = tid
    return tasks
