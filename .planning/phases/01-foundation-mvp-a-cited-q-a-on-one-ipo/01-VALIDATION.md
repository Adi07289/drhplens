---
phase: 1
slug: foundation-mvp-a-cited-q-a-on-one-ipo
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `01-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python 3.11+) |
| **Config file** | `pyproject.toml` (Wave 0 task installs) |
| **Quick run command** | `pytest tests/unit -x -q --timeout=10` |
| **Full suite command** | `pytest tests/ -x -q --timeout=60` |
| **Estimated runtime** | unit < 10 sec; full suite < 60 sec; eval opt-in via `--run-eval` |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit -x -q --timeout=10`
- **After every plan wave:** Run `pytest tests/ -x -q --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green; eval suite run once on the gold set
- **Max feedback latency:** 10 seconds for unit tests, 60 seconds for full suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-W0-pyproject | 01 | 0 | (infra) | — | N/A | manual | `python -c "import streamlit, langgraph, llama_index, docling, qdrant_client, langfuse, pydantic"` | ❌ W0 | ⬜ pending |
| 1-01-claim_id-schema | 01 | 1 | INGEST-03, RAG-02, TRUST-04 | T-1-02 | Schema rejects malformed input; `claim_id` is required + unique within answer | unit | `pytest tests/unit/test_schemas.py -x` | ❌ W0 | ⬜ pending |
| 1-01-scrubber-banned | 01 | 1 | TRUST-02 | T-1-01 | Every banned token (subscribe/avoid/buy/sell/target/recommend/fair value/overvalued/undervalued/target price) triggers hard block + regenerate, then refusal | unit | `pytest tests/unit/test_scrubber.py -x` | ❌ W0 | ⬜ pending |
| 1-01-disclaimer-render | 01 | 1 | TRUST-01, TRUST-03 | — | Three surfaces (modal + persistent footer + per-answer footer) render with anchor copy; 12px ≥ SEBI 10pt floor | unit | `pytest tests/unit/test_disclaimer_surface.py -x` | ❌ W0 | ⬜ pending |
| 1-02-docling-parse | 02 | 2 | INGEST-01, INGEST-02 | — | Swiggy DRHP parses to JSON with page anchors + section structure; financial tables extract without merged-cell mangling | unit | `pytest tests/unit/test_parser.py -x` | ❌ W0 | ⬜ pending |
| 1-02-chunker | 02 | 2 | INGEST-02, INGEST-03 | — | Section-aware chunker preserves page anchors on every chunk; chunk size within target band | unit | `pytest tests/unit/test_chunker.py -x` | ❌ W0 | ⬜ pending |
| 1-02-embedder | 02 | 2 | INGEST-03 | — | bge-m3 embedder produces 1024-d vectors; deterministic given same input | unit | `pytest tests/unit/test_embedder.py -x` | ❌ W0 | ⬜ pending |
| 1-02-qdrant-upsert | 02 | 2 | INGEST-03 | — | Qdrant client connects + upserts + retrieves; collection size after Swiggy ingestion within 1GB budget | integration | `pytest tests/integration/test_qdrant_ingest.py -x` | ❌ W0 | ⬜ pending |
| 1-03-retrieve | 03 | 3 | RAG-01 | — | Retrieve+rerank returns top-k chunks with scores; ordering matches reranker rubric | unit | `pytest tests/unit/test_retrieve.py -x` | ❌ W0 | ⬜ pending |
| 1-03-gate1-floor | 03 | 3 | RAG-03 | — | Below-threshold max-score triggers refusal node, never reaches LLM call | unit | `pytest tests/unit/test_gate1.py -x` | ❌ W0 | ⬜ pending |
| 1-03-cite-check | 03 | 3 | RAG-02, TRUST-04 | T-1-02 | Cite-check rejects any answer where any claim's span fails token_set_ratio or number-set subset check | unit | `pytest tests/unit/test_cite_check.py -x` | ❌ W0 | ⬜ pending |
| 1-03-decompose-multi | 03 | 3 | RAG-01 | — | Multi-part question splits into sub-questions; D-06 partial-answer flag preserved | unit | `pytest tests/unit/test_decompose.py -x` | ❌ W0 | ⬜ pending |
| 1-03-langgraph-e2e | 03 | 3 | RAG-01, RAG-02, RAG-03, TRUST-04 | T-1-01, T-1-02 | End-to-end agent runs on fixture gold-set question and emits a cited grounded answer OR a refusal with reformulation | integration | `pytest tests/integration/test_agent_e2e.py -x` | ❌ W0 | ⬜ pending |
| 1-04-citation-chip-html | 04 | 4 | UI-02 | T-1-06 | Citation chip renderer emits `<sup>` with `aria-describedby` and dedupes per-cluster; XSS-attempt input is escaped | unit | `pytest tests/unit/test_citation_renderer.py -x` | ❌ W0 | ⬜ pending |
| 1-04-streamlit-app-smoke | 04 | 4 | UI-01, UI-02, TRUST-01 | — | `streamlit run app.py` boots cleanly; home + /methodology pages render | manual | `bash scripts/smoke.sh` | ❌ W0 | ⬜ pending |
| 1-05-deploy-smoke | 05 | 5 | OPS-02 | T-1-03 | Public HF Spaces URL returns 200 + renders home page within 60s of cold start | manual | curl + visual | — | ⬜ pending |
| 1-05-langfuse-trace | 05 | 5 | (cross-cutting `claim_id` invariant) | — | Every agent run writes a Langfuse trace with `claim_id` propagated through every claim node | integration | `pytest tests/integration/test_langfuse_trace.py -x --run-langfuse` | ❌ W0 | ⬜ pending |
| 1-05-eval-gold-set | 05 | 5 | RAG-01, RAG-02, RAG-03, TRUST-04 | — | 10-15 hand-curated gold-set Q/A/source-span entries (5 factual, 3 numeric, 3 risk-factor, 2 refusal-eligible) all pass faithfulness + recall@k checks at Phase 1 baseline thresholds | eval | `pytest tests/eval -x --run-eval` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — declare pytest 8.x, ruff, mypy, plus the locked stack (streamlit>=1.36,<2; langgraph>=1.2,<2; llama-index>=0.14,<0.15; docling>=2.95,<3; qdrant-client>=1.12,<2; langfuse>=2.x; pydantic>=2,<3; instructor; sentence-transformers; FlagEmbedding)
- [ ] `tests/conftest.py` — shared fixtures (fixture DRHP, mock Qdrant, mock LLM, gold-set loader)
- [ ] `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/eval/__init__.py`
- [ ] Stub test files for every Per-Task Verification Map row above (red imports OK at Wave 0; bodies fill in their respective waves)
- [ ] `tests/eval/gold_set.jsonl` — 10–15 hand-curated entries (Wave 0 stubs the schema; full content lands in Wave 5)
- [ ] `data/swiggy_drhp/swiggy-drhp.pdf` + `data/swiggy_drhp/SHA256SUMS` — pinned binary
- [ ] `pipelines/ingest_swiggy.py` stub — offline ingestion script invoked manually in Wave 2

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Citation chip click expands inline + shows DRHP source span + links to SEBI PDF page | UI-02 | Streamlit interaction-level behavior not easily asserted in headless tests; covered by smoke test | Run `streamlit run app.py`, ask "what is the use of proceeds?", click `[1]` chip, verify inline expander shows the cited DRHP span + SEBI link opens correct page |
| First-use modal appears on first visit + persists "I understand" via `st.session_state` | TRUST-01 | Streamlit session-state persistence is hard to assert in unit tests; covered by smoke test | Open public HF Spaces URL in incognito, verify modal appears, click "I understand", refresh page within same session, verify modal does not re-appear |
| Cold-start UX displays "warming up" copy + auto-dismisses on readiness | OPS-02, P19 | HF Spaces cold-start timing nondeterministic | Wait > 30 min, visit public URL, observe loading state, verify auto-dismiss when LangGraph agent reports ready |
| Mobile responsive at 375 / 640 / 1024px breakpoints (citation chips remain tappable at 44×44px) | UI-01 | Visual + interaction assertion needs human eyes | Chrome DevTools device emulation; verify per UI-SPEC mobile contract |
| SEBI legal-review checkpoint | TRUST-03 | Out of Phase 1 scope — final gate before Phase 6 public launch (per ROADMAP cross-cutting) | Document review, not code |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (unit: < 10s; full: < 60s)
- [ ] `nyquist_compliant: true` set in frontmatter (after Wave 0 ships and all stub tests resolve)

**Approval:** pending
