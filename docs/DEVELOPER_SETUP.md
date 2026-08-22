# Developer Setup

## Prerequisites
- Python **3.11+** (developed on 3.14)
- (optional) A model API key and/or Supabase project for non-offline runs

## 1. Clone & branch
```bash
git clone https://github.com/Satvik2813/Kalki.git
cd Kalki
git checkout dev/satvik-core        # core lives here; do not commit to main
```

## 2. Install
The **core needs nothing** — it runs on the stdlib. For tests + API:
```bash
python -m pip install -r requirements.txt      # fastapi, uvicorn, pytest, httpx, ...
# or, editable with extras:
python -m pip install -e ".[dev]"
```

## 3. Configure (optional)
```bash
cp .env.example .env
# defaults are offline-first: mock model + local SQLite memory
```
Key switches:
- `KALKI_MODEL_PROVIDER` = `mock` | `omniroute` | `anthropic` | `openai`
- `KALKI_MEMORY_BACKEND` = `local` | `supabase`
- `KALKI_AUTONOMY` = `supervised` (gate elevated/dangerous) | `autonomous`

## 4. Run
```bash
python scripts/demo.py                 # full closed-loop demo (offline)
python -m pytest -q                    # 33 tests
uvicorn api.app:app --reload           # API at http://127.0.0.1:8000/docs
```

## 5. Real backends

### Model providers
```bash
KALKI_MODEL_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-...   python scripts/demo.py
# OmniRoute gateway (auto-falls back to direct/mock if unreachable):
KALKI_MODEL_PROVIDER=omniroute OMNIROUTE_BASE_URL=http://localhost:8080
```
Install SDKs as needed: `pip install 'kalki[anthropic]'` / `'kalki[openai]'`.

### Supabase + pgvector
```bash
pip install 'kalki[supabase]'
export KALKI_MEMORY_BACKEND=supabase
export SUPABASE_DB_URL='postgresql://user:pass@host:5432/postgres'
```
The store auto-provisions the `vector` extension, `kalki_memories` table and
indexes on first run. If the connection fails, KALKI logs a warning and falls
back to the local store rather than crashing.

## 6. Integrating (Dev 2 / Dev 3)
- **Tools (Dev 3):** implement `agent.tools.base.Tool`, register it in the
  service's registry. See `docs/CONTRACTS.md`.
- **Frontend (Dev 2):** use the REST + SSE API in `docs/CONTRACTS.md §API`.
- Keep changes behind the documented contracts; the core stays stable.

## 7. Project conventions
- Work on `dev/satvik-core`; never `git push origin main`.
- Before major integration: `git fetch origin && git rebase origin/main`.
- Run `python -m pytest -q` before pushing a milestone.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `No module named pytest` | `pip install -r requirements.txt` |
| API import error about FastAPI | `pip install 'kalki[api]'` |
| Supabase errors | check `SUPABASE_DB_URL`; falls back to local automatically |
| `pytest.exe not on PATH` warning | harmless; use `python -m pytest` |
