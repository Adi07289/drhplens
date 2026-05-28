# Plan 01-04 — Wave 3 SUMMARY

**Status:** ✅ code complete · ⏸ live Walking Skeleton demo deferred (needs GEMINI_API_KEY + QDRANT live)

---

## Commits (6 atomic, all green)

| Hash | Task | What landed |
|------|------|-------------|
| `b84ee33` | T1 | Read-side nodes (intake, retrieve, rerank, gate1_check, decompose) + `agent/policies.py` + synthetic-chunks fixture |
| `1ecbf2a` | T2 | Generate node — Instructor + Gemini structured output (GroundedAnswer); versioned `agent/prompts/generate.md` with T-1-02 neutrality clause |
| `5e3eb92` | T3 | Scrub + cite_check + emit — non-LLM cite-check (token_set_ratio ≥80 + numeric-set subset); D-09 hard-block-and-regenerate (MAX_REGENERATE_ATTEMPTS=1) |
| `6e5c9eb` | T4 | Refuse_with_reformulation — deterministic top-2 unique sections from `search_relaxed()` (Open Question 5 resolution; no LLM call) |
| `1ffd3fb` | T5 | `agent/graph.py` — LangGraph StateGraph topology per SKELETON §C with conditional edges to `refuse_with_reformulation` at gate1 / gate2 / scrubber-second-fail |
| `acd70ed` | T6 | `agent/demo.py` Typer CLI + integration tests (`test_agent_e2e.py`, `test_drhp_prompt_injection.py`) |

---

## Test Status

**176 unit tests passing** (Waves 0+1+2+3). +48 from Wave 2's 128.

Deferred (xfail with `run=False`, gated on user setup):
- `tests/integration/test_agent_e2e.py` — needs GEMINI_API_KEY + live Qdrant
- `tests/integration/test_drhp_prompt_injection.py` — same
- `tests/integration/test_qdrant_ingest.py` — same (deferred since Wave 2)

---

## Walking Skeleton Status

**Code-complete:** `agent/demo.py` + `agent/graph.py` + 10 LangGraph nodes all import cleanly. `python -c "from agent import graph; print(graph.GRAPH)"` returns a compiled StateGraph.

**Live demo deferred:** `python -m agent.demo "..."` will fail at runtime without `GEMINI_API_KEY` (generate node) and a populated Qdrant collection (retrieve node). Both are user-setup steps documented in `data/swiggy_drhp/INGEST_LATER.md`.

---

## To Actually Run the Walking Skeleton

```bash
# 1. Verify .venv is on Python 3.11 + full stack
cd ~/agentic-rag-app && source .venv/bin/activate
python -c "import torch, docling, sentence_transformers, langgraph; print('OK')"

# 2. Start Qdrant
docker run -d -p 6333:6333 -p 6334:6334 \
  -v ~/.qdrant/drhplens:/qdrant/storage \
  --name drhplens-qdrant qdrant/qdrant

# 3. Add keys to .env
cat >> .env <<'EOF'
GEMINI_API_KEY=<your-key-from-aistudio.google.com/apikey>
GROQ_API_KEY=<your-key-from-console.groq.com/keys>
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
EOF

# 4. Ingest Swiggy DRHP for real
python -m pipelines.ingest_swiggy

# 5. Run the Walking Skeleton CLI
python -m agent.demo "what is the use of proceeds?"
python -m agent.demo "what is the weather in Mumbai?"   # expect refusal + reformulation

# 6. Flip integration tests green
pytest tests/integration/ -x
```

---

## Deviations

1. **Real Docling re-parse not attempted** — venv recreate + heavy dep install consumed the executor's budget. Docling cache stays `1.0.0-pymupdf-fallback` (34 sections). Real re-parse can run as a one-line step once the user verifies the new venv: `python -m pipelines.ingest_swiggy --dry-run` (will replace the cache if Docling now works).

2. **Executor watchdog killed at 600s no-progress** mid-way through writing the SUMMARY.md. All 6 task commits landed cleanly before the stall; the lost work was just the summary doc itself (this file, recovered inline).

---

## Coverage Update (REQUIREMENTS.md)

Wave 3 covers RAG-01, RAG-02, RAG-03, TRUST-04. Status markers: keep as `[~]` (code-complete; runtime verification pending API keys + live Qdrant). Flip to `[x]` after the user runs steps 1-6 above and the integration tests pass.

---

## Recommended Next Step

**Wave 4 — Streamlit UI (01-05-PLAN.md).** No new API keys needed (uses Wave 3's Gemini key when actually run). Wave 4 wraps the agent in the cited-Q&A page + 3 disclaimer surfaces + refusal banner + /methodology stub + mobile responsive CSS.
