# KALKI — Autonomous AI Software Engineer

> Give KALKI **one** engineering objective. It plans, inspects the repo, uses
> tools, changes code, runs tests, recovers from failures, deploys, verifies
> the result, and remembers what it learned — as a stateful closed loop, not a
> single prompt→response.

KALKI is built for the **LaunchPadX "Agent Hub"** challenge. This repository is
the **core / backend / agent brain** (Developer 1 ownership): the planner, the
stateful orchestrator, the memory system, the tool interfaces, the recovery &
verification engines, and the API that the frontend and tool authors build on.

```
OBJECTIVE → UNDERSTAND → PLAN → INSPECT → USE TOOLS → MODIFY CODE → RUN TESTS
    → OBSERVE → (FAILURE? → DIAGNOSE → REPLAN → FIX) → DEPLOY → VERIFY
    → STORE EXPERIENCE → COMPLETE
```

## Why it satisfies the hackathon requirements

| Requirement | How KALKI meets it |
|---|---|
| **Planning & decision making** | `agent/planner.py` decomposes an objective into an ordered, dependency-aware `Plan`; the orchestrator selects tasks and re-plans dynamically from tool results. |
| **Tool usage** | `agent/tools/` defines a stable `Tool` interface + registry; built-ins cover filesystem, shell/tests, HTTP checks, deploy. External APIs/DBs plug in without touching the core. |
| **Memory management** | `memory/` implements **session / project / long-term** memory over SQLite+vectors (local) or **Supabase + pgvector**; long-term retrieval *influences the plan*. |
| **Autonomous execution** | `agent/orchestrator.py` is a persistent **state machine** over `AgentState` that drives an objective to completion with recovery, not a stateless chatbot. |
| **Not a single prompt→response** | Execution state is explicit, serialisable, resumable, and observable via a real-time event stream. |

## Quickstart (zero config, fully offline)

The core runs on the **Python standard library only** — no API keys, no
network, no database. The default model is a deterministic mock and memory is
local SQLite.

```bash
# 1) See the whole closed loop, including a recovered failure:
python scripts/demo.py

# 2) Run the test suite (33 tests: planner, state machine, recovery,
#    memory, verification, API, and the end-to-end integration test):
pip install pytest fastapi httpx
python -m pytest -q
```

### Run the API

```bash
pip install -r requirements.txt
uvicorn api.app:app --reload
# open http://127.0.0.1:8000/docs
```

```bash
# Create + start an objective, then stream events:
curl -X POST localhost:8000/api/tasks \
  -H 'content-type: application/json' \
  -d '{"objective":"Fix the auth bug, test, deploy, verify","start":true,"autonomy":"autonomous"}'
# -> {"id":"run-XXXX", ...}
curl -N "localhost:8000/api/tasks/run-XXXX/events?stream=1"
```

## Using real models / real memory

Everything is a swappable adapter selected by environment (see `.env.example`):

```bash
# Direct providers or an OmniRoute gateway (with automatic fallback):
KALKI_MODEL_PROVIDER=anthropic   ANTHROPIC_API_KEY=...      # or openai / omniroute / mock
# Supabase + pgvector for scalable memory:
KALKI_MEMORY_BACKEND=supabase    SUPABASE_DB_URL=postgres://...
```

The core **never depends on OmniRoute directly**: if it is unreachable, the
registry falls back to a direct provider, then to the mock (see
`models/registry.py`).

## Repository layout

```
Kalki/
├── shared/         # contracts.py — the stable integration types (Task, Plan, ...)
├── agent/          # brain: planner, orchestrator (state machine), recovery,
│   └── tools/      #        verification, permissions, events, built-in tools
├── memory/         # session/project/long-term memory (local + Supabase/pgvector)
├── models/         # ModelProvider abstraction (mock / omniroute / anthropic / openai)
├── backend/        # KalkiService — run lifecycle over the core
├── api/            # FastAPI app + SSE event stream
├── config/         # settings (env-driven, offline-first defaults)
├── scripts/        # demo.py
├── tests/          # full suite incl. the required integration test
└── docs/           # ARCHITECTURE, CONTRACTS, AGENT_FLOW, DEVELOPER_SETUP
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components & design decisions
- [`docs/AGENT_FLOW.md`](docs/AGENT_FLOW.md) — the state machine & event lifecycle
- [`docs/CONTRACTS.md`](docs/CONTRACTS.md) — stable interfaces for Dev 2 & Dev 3
- [`docs/DEVELOPER_SETUP.md`](docs/DEVELOPER_SETUP.md) — environment & integration guide

## Status

Core engine complete and tested (33 passing tests). Built on branch
`dev/satvik-core`. Integration surfaces are stable — see `docs/CONTRACTS.md`.
