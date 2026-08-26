# DRHPLens API (FastAPI over the brain)

A thin request/response wrapper over the existing brain (`agent/`, `pipelines/`,
`tools/`). No brain changes — it imports and calls them.

## Run locally

```bash
cd ~/agentic-rag-app
set -a; source .env; set +a          # load GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY, LLM_PROVIDER
.venv/bin/uvicorn api.main:app --reload --port 8000
```

On Render/HF the env vars are set by the platform, so the `source .env` step is
local-only.

## Endpoints

- `GET  /health` → `{"status": "ok"}`
- `GET  /forecast/{drhp_id}` → `{"state": "covered"|"abstain"|"not_found", "record": {...}|null}`
- `POST /ask` `{ "question": str, "drhp_id": str }` → `{"kind": "fused"|"grounded"|"refusal", "answer": {...}}`

Answer priority mirrors the Streamlit chat: `fused_answer` → `grounded_answer` → `refusal`.

## Tests

```bash
.venv/bin/python -m pytest api/tests -v   # brain is monkeypatched — no keys needed
```
