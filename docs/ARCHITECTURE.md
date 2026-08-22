# KALKI Architecture

KALKI is a **stateful, closed-loop autonomous engineering agent**. This document
describes the core components (Developer 1 ownership) and the key design
decisions behind them.

## 1. High-level shape

```
                         ┌─────────────────────────────────────────────┐
   objective ──────────► │                Orchestrator                 │
                         │        (state machine over AgentState)      │
                         └───┬───────┬───────┬───────┬────────┬────────┘
                             │       │       │       │        │
                        Planner   Tools   Recovery Verifier  EventBus
                             │       │       │       │        │
                    ModelProvider  Registry │       │     (SSE/poll)
                             │               │       │
                          Memory  ◄──────────┴───────┘
                       (session / project / long-term)
```

Every arrow is an interface (see `docs/CONTRACTS.md`). The orchestrator depends
only on abstractions — `ModelProvider`, `Tool`/`ToolRegistry`, `MemoryStore` —
so concrete backends (OmniRoute, Supabase, Dev 3's tools) are swappable without
touching the core.

## 2. Components

### Contracts (`shared/contracts.py`)
Dependency-free, JSON-serialisable dataclasses + enums: `Task`, `Plan`,
`ToolSpec`, `ToolResult`, `MemoryRecord`, `MemoryResult`, `AgentEvent`,
`AgentState`, `ExecutionResult`. These are the stable spine of the system.

### Model abstraction (`models/`)
`ModelProvider` exposes a single primitive, `complete()`, plus higher-level
`plan()`/`decide()` helpers. Providers:
- **MockProvider** — deterministic, offline; the default and the one tests use.
- **OmniRouteProvider** — OpenAI-compatible gateway over stdlib HTTP.
- **DirectAnthropicProvider / DirectOpenAIProvider** — SDK-based, lazy-imported.

`models/registry.py` resolves the requested provider and **falls back**
(omniroute → anthropic → openai → mock) if it is unavailable. The core never
imports OmniRoute — only the registry does, at the edge.

### Planning (`agent/planner.py`)
Turns an objective into a `Plan` (via the provider), injecting **retrieved
long-term memories** into the planning context so past incidents influence the
plan. `revise_after_failure()` performs dynamic replanning: it inserts a
remediation task and re-queues the failed task.

### Orchestrator (`agent/orchestrator.py`)
An explicit state machine over `AgentState` (see `docs/AGENT_FLOW.md`). It owns
the execution loop: select task → permission-gate → execute tool → observe →
decide (retry/replan/escalate/abort) → … → verify → store memory. State is
persistent, serialisable and **resumable** (used for human-approval pauses).

### Tools (`agent/tools/`)
`Tool` = `ToolSpec` + `run(args, ctx) → ToolResult`. `Tool.invoke()` adds timing
and exception-safety so a tool never crashes the loop — unexpected errors become
classified `ToolResult` failures. Built-ins: `read_file`, `write_file`,
`list_dir`, `run_command`, `run_tests`, `http_check`, `deploy`. All filesystem
tools are **sandboxed** to `workspace_root`.

### Memory (`memory/`)
Three layers over one `MemoryStore` interface:
- **session** — objective, plan, tool calls, errors for the current run
- **project** — durable per-repository knowledge
- **long-term** — engineering experience (incidents, bugs, fixes), vector-retrieved

Backends: `LocalMemoryStore` (SQLite + in-process cosine over a dependency-free
hashed embedder) and `SupabaseMemoryStore` (Postgres + pgvector). Retrieval
**influences decisions** via `MemoryManager.recall_experience()`.

### Recovery (`agent/recovery.py`)
Classifies a failure (`transient / tool_error / logic_error / permission /
fatal`) and chooses `RETRY | REPLAN | ESCALATE | ABORT`, bounded by
`max_task_retries` and `max_plan_revisions` — KALKI never retries forever.

### Verification (`agent/verification.py`)
An action succeeding ≠ the objective being done. The verifier independently
confirms: all tasks terminal-good, tests actually passed, and any deploy URL
answers a smoke check. The terminal status distinguishes
`COMPLETED / FAILED / BLOCKED / AWAITING_APPROVAL`.

### Permissions (`agent/permissions.py`)
Risk-tiered gating (`safe / elevated / dangerous`) with an autonomy mode.
Dangerous actions (e.g. prod rollback, destructive DB ops) always require human
approval, pausing the run in `AWAITING_APPROVAL` until `approve()` resumes it.

### Events (`agent/events.py`) & Backend (`backend/service.py`)
The orchestrator emits `AgentEvent`s through an `EventBus` that buffers history
so late subscribers replay everything. `KalkiService` manages run lifecycle
(create/start/approve/query) on background threads; the API is a thin shell over
it.

## 3. Key design decisions

**Offline-first, adapters at the edge.** The PRD mandates Supabase+pgvector and
an OmniRoute gateway. Depending on them directly would make the core
unbuildable/untestable here. Instead each mandated service is an optional
adapter behind a minimal interface with an always-available default (mock model,
local SQLite). The mandated backend becomes a *configuration choice*, and the
whole engine + tests run with zero network/credentials.

**Explicit state machine over LangGraph.** The PRD names LangGraph as *preferred
if it provides clear value*. We implement a dependency-free state machine
because it (a) keeps the core installable/testable offline, (b) gives full
control over the recovery/replan edges, and (c) serialises cleanly to
`AgentState` for pause/resume. The node set maps 1:1 onto a LangGraph graph, so
adopting LangGraph later is mechanical, not a rewrite.

**Tools never raise.** Expected failures are returned as classified
`ToolResult`s; only that makes principled recovery possible.

**Verification is mandatory.** The loop cannot reach `COMPLETED` without the
verifier passing, preventing "the API returned 200 so we're done" false
positives.

## 4. Extension points (Dev 2 / Dev 3)

- **Dev 3 (tools):** implement `Tool`, register it; the planner can reference it
  by name. No core change required.
- **Dev 2 (frontend):** consume the REST + SSE API (`docs/CONTRACTS.md §API`).
  Every execution moment is an `AgentEvent`.
