# Phase 1 — Foundation + MVP-A: Cited Q&A on One IPO — PHASE CLOSE

**Date:** 2026-05-28
**Status:** CODE-COMPLETE — awaiting user_setup (OPS-02 live deploy + Phase 1 formal sign-off)

---

## What Shipped (28+ commits across 5 waves)

### Wave 0 (Plan 01) — Scaffold
Repo skeleton, pyproject.toml, SKELETON.md, gold_set.jsonl schema, .gitignore, SHA-256 DRHP pin,
conftest fixtures, Wave 0 tests (drhp_integrity, schemas). 219 unit tests established as baseline.

### Wave 1 (Plan 02) — Schemas + compliance primitives
`agent/schemas.py` (GroundedAnswer, Claim, CitationSource, RefusalResponse, SubQuestions),
`compliance/scrubber.py` (banned-token regex), `ui/copy.py` (D-07 anchor copy + disclaimer surfaces),
`ui/citation_renderer.py` (chip HTML). TRUST-01, TRUST-02, TRUST-04 primitives landed.

### Wave 2 (Plan 03) — Ingestion pipeline
Docling PDF parser, chunker (512-1024 tokens, 100-200 token overlap, section-aware),
Qdrant upsert with `{drhp_id, section, page_start, page_end, chunk_text}` payload,
bge-m3 embedder, INGEST-01/02/03 tests passing.

### Wave 3 (Plan 04) — Agent graph
Full 10-node LangGraph graph: intake → retrieve → rerank → gate1_check → decompose →
generate → scrub → cite_check → refuse_with_reformulation → emit.
Three refusal branches (Gate 1, Gate 2, scrub-exhausted). agent.demo CLI. RAG-01/02/03.

### Wave 4 (Plan 05) — Streamlit UI
app.py with st.cache_resource singletons, first-use modal (D-08), persistent footer,
per-answer footer, citation chips (UI-02), mobile-responsive layout (UI-01),
pages/01_methodology.py stub, Plotly charts scaffold.

### Wave 5 (Plan 06 — this plan)
README.md HF Spaces YAML frontmatter, .env.example (7 keys), docs/DEPLOY.md (12-step runbook),
Langfuse instrumentation with no-op fallback, invoke_with_tracing() wrapper,
13-entry gold set, run_eval.py, calibrate_gate1.py, cron_pinger.yml.

---

## Offline vs Online Capability

| Capability | Status | Blocker |
|---|---|---|
| Agent answers questions with citations | offline OK | None — runs on localhost with .env |
| Refusal posture (Gate 1 + Gate 2) | offline OK | None |
| Streamlit UI (app.py) | offline OK | `streamlit run app.py` with .env |
| Langfuse traces | offline: no-op | Needs LANGFUSE_PUBLIC_KEY in .env or HF secrets |
| Public URL (OPS-02) | awaiting | User_setup T4: create HF Space, configure secrets |
| Cold-start mitigation | code-ready | sleep_time:1800 in README.md; cron pinger needs user setup |
| Eval baseline report | awaiting | User_setup T4: run `python scripts/run_eval.py` |
| GATE1_THRESHOLD calibrated | code-ready | User_setup T5: run `python scripts/calibrate_gate1.py` |

---

## Phase 1 REQ Scorecard

13 of 13 REQs have code-level closure. OPS-02 is the only REQ pending live verification.

| REQ | Wave | Code status | Live verification |
|---|---|---|---|
| INGEST-01 | 0 | passing unit tests | — |
| INGEST-02 | 2 | passing unit tests | — |
| INGEST-03 | 2 | passing unit tests | — |
| RAG-01 | 3+4 | passing unit+integration | needs live URL smoke test |
| RAG-02 | 1+3+4 | passing unit tests | needs live URL chip test |
| RAG-03 | 3 | passing unit tests | needs live URL refusal test |
| TRUST-01 | 1+4 | passing unit tests | needs live URL three-surfaces check |
| TRUST-02 | 1+3 | passing unit tests | needs live URL Gate 2 test |
| TRUST-03 | 1+3 | passing unit tests | legal review deferred to Phase 6 |
| TRUST-04 | 1+3 | passing unit tests | — |
| UI-01 | 4 | passing unit tests | needs 375px DevTools check on live URL |
| UI-02 | 4 | passing unit tests | needs chip click on live URL |
| **OPS-02** | **5** | **code-complete** | **BLOCKED: user must create HF Space + configure secrets** |

---

## What's Locked for Phase 2 Inheritance (per SKELETON §F-G)

- **SKELETON §A-D** (schemas, cite-check algorithm, banned-token list, graph topology) — frozen
- **Agent state shape** (GraphState keys) — frozen; Phase 2 adds `ipo_id` without changing existing keys
- **Disclaimer copy** (D-07 anchor copy, TRUST-01 three surfaces, TRUST-02 Gate 2 wording) — frozen
- **Citation chip HTML/CSS** — frozen for Phase 1 scope; Phase 2 adds multi-IPO selector without touching chips
- **Langfuse trace shape** (9-span topology + claim_id metadata contract) — frozen for Phase 3 METHOD-01

## What's Plastic (may tune in Phase 3+)

- `GATE1_THRESHOLD` — will re-calibrate in Phase 3 against the larger multi-IPO gold set
- `CITE_CHECK_TOKEN_RATIO` — may loosen if numeric faithfulness tests show over-refusal
- `MAX_REGENERATE_ATTEMPTS` — may increase to 2 in Phase 3 if scrub-exhaustion rate is high

---

## CEO Review T6 Callouts — Status

| Callout | Status | Location |
|---|---|---|
| HF Spaces cold-start cron pinger | documented; Option A (cron-job.org) + Option B (scripts/cron_pinger.yml) | docs/DEPLOY.md Step 8 |
| Qdrant 1GB sizing callout | documented | docs/DEPLOY.md Prerequisites |
| METHOD-01 (methodology pane) pulled forward | Langfuse claim_id contract wired in Phase 1 code | app/observability/ + agent/graph.py |

---

## Phase 1 Lessons for Phase 2 Retrospective

1. **No-op fallback pattern is essential** — every external service (Langfuse, Qdrant, Gemini) needs an is_enabled()-gated no-op path so local dev and CI without full credentials work.
2. **Gold set content is user-setup** — the 13 entries are reasonable starter content but expected_answer_contains values are approximations; a human reading the actual DRHP should validate page ranges and financial figures before Phase 3 sets release gates against them.
3. **Wave 0 schema stubs create mild friction** — the `"refusal"` vs `"refusal-eligible"` category name diverged between Wave 0 stubs and Wave 5 spec; future plans should lock stub field values, not just field names.
4. **sleep_time: 1800 is the correct HF Spaces cold-start mitigation** — do not increase; HF free tier rejects values above 1800.
