---
phase: 1
slug: foundation-mvp-a-cited-q-a-on-one-ipo
type: walking-skeleton
ships_at: end-of-wave-3
status: planned
created: 2026-05-28
---

# Walking Skeleton — Phase 1 (DRHPLens MVP-A)

> The thinnest possible end-to-end stack that proves the architecture works. Ships at the close of Wave 3. Subsequent waves polish (UI, deploy, eval, observability). This document records the **architectural skeleton** decisions that every later phase will build on without renegotiating.

---

## What the Skeleton Is

A user (developer, locally) can:

1. Run `python -m pipelines.ingest_swiggy` once. The Swiggy DRHP (Nov 2024) is parsed by Docling, chunked section-aware, embedded with bge-m3, and upserted to Qdrant Cloud — fully offline, build-time, deterministic.
2. Run `python -m agent.demo "What is Swiggy's issue size?"` and receive a `GroundedAnswer` Pydantic object on stdout containing prose with `{{claim_id}}` placeholders + a `claims: [Claim]` array — every claim has a verified `RetrievedChunkRef` and the deterministic non-LLM `cite_check` node has passed.
3. Run `python -m agent.demo "What does Swiggy say about Mars colonization?"` and receive a structured refusal with reformulation suggestions sourced from the top retrieved sections — Gate 1 (retrieval-score floor) refusal path exercised.
4. Run `python -m agent.demo "Should I subscribe to Swiggy?"` and receive a structured refusal — Gate 2 (banned-token scrubber → cite-check → refuse) path exercised.

The skeleton has NO UI, NO deployment, NO Langfuse. Those layers are deliberate polish in Waves 4-5. The skeleton proves the contracts; the polish proves the demo.

---

## Architectural Decisions (locked at end of Wave 3; do NOT renegotiate in later phases)

### A. Storage as the Integration Bus

- **Vector store:** Qdrant Cloud free 1GB cluster (collection: `drhp_chunks`). HF Spaces `/tmp` is volatile, so embedded Qdrant is forbidden.
- **Object store for raw artifacts:** committed to git under `data/swiggy_drhp/` — the PDF (binary) + the parsed Docling JSON + a SHA-256 pin. Phase 2's multi-IPO catalogue will migrate to HF datasets when the repo exceeds GitHub's 100 MB limit.
- **No relational DB in Phase 1.** All chunk metadata lives in Qdrant payload. Phase 4's historical IPO dataset will introduce SQLite/Postgres.
- **No feature store in Phase 1.** Phase 5's forecaster introduces one (Parquet on disk).
- **Rule:** Batch pipelines (`pipelines/*`) only write. Runtime agent (`agent/*`) only reads. No batch-to-runtime in-process call. No runtime-to-batch call. Ever.

### B. Schema Contract (load-bearing — Phase 3 METHOD-01 consumes verbatim)

The Pydantic v2 schemas in `agent/schemas.py` are the most load-bearing artifacts in the entire project. Once Wave 1 ships them, every later phase imports them unchanged:

- `RetrievedChunkRef` — `{ chunk_id, page_start, page_end, section, span_offsets }` — Qdrant payload row → claim source.
- `Claim` — `{ claim_id (pattern `^c_[a-z0-9]{6,16}$`), text, sources: list[RetrievedChunkRef] (min_length=1) }`.
- `GroundedAnswer` — `{ answer_prose (with `{{claim_id}}` placeholders), claims, sub_question_addressed, sub_question_unaddressed }`.
- `RefusalReason` — enum: `low_retrieval_score | unsupported_claim | banned_token | infrastructure_error`.
- `RefusalResponse` — `{ reason: RefusalReason, message: str, reformulation_suggestions: list[str] (max_length=3) }`.

**Cross-cutting invariant from ROADMAP:** every claim carries a `claim_id`; renderer resolves citations; cite-check is non-LLM. The schemas above are how that invariant becomes code.

### C. The LangGraph Topology

Phase 1 is a strict linear DAG with three refusal branches. Zero cycles. The "regenerate-once on scrubber failure" is a counter-bounded conditional, not a loop.

```
intake → retrieve → rerank → gate1_check
                              │
                              ├─ score < τ → refuse_with_reformulation → END
                              └─ score ≥ τ → decompose → generate → scrub
                                                                   │
                                                                   ├─ banned (try 1) → generate
                                                                   ├─ banned (try 2) → refuse_with_reformulation → END
                                                                   └─ clean → cite_check
                                                                              │
                                                                              ├─ unsupported claim → refuse_with_reformulation → END
                                                                              └─ all grounded → emit → END
```

Phase 6 may upgrade to a supervised multi-agent topology. Phases 2-5 do NOT rewrite this graph; they extend it with new nodes that respect the same state shape.

### D. The Cite-Check Algorithm (deterministic, non-LLM, < 100 ms)

`agent/nodes/cite_check.py` runs after `scrub` and before `emit`. For each `Claim` in the `GroundedAnswer`:

1. Look up the cited `chunk_text` from the retrieval payload via `claim.sources[i].chunk_id`.
2. Take a ±50-character window around `claim.sources[i].span_offsets`.
3. Normalize both strings (Unicode NFKC, lowercase, collapse whitespace, strip non-`\w\s.,%₹-`).
4. Primary check: `rapidfuzz.fuzz.token_set_ratio(claim_text, window) >= 80`.
5. Secondary check: every numeric token (regex `\d[\d,.\-]*`) in the claim must appear verbatim in the window.
6. If both pass for any source, the claim is grounded.
7. If any claim is not grounded, the whole answer is rejected; refusal path fires.

LLM-judge fallback is FORBIDDEN. Numeric-tolerance is FORBIDDEN (no rounding allowed in financial RAG — PITFALL P2 / P5). Phase 3's METHOD-01 will surface per-claim cite-check results in the "Show your work" pane.

### E. The Compliance Module

`compliance/banned_tokens.py` is the regex source-of-truth. Phase 1 locks the token list at (case-insensitive, with `\w*` suffix for morphological variants):

```
subscribe, avoid, buy, sell, target, recommend,
fair value, overvalued, undervalued, target price,
accumulate, outperform, underperform, book profits, bullish, bearish
```

The scrubber runs hard-block-and-regenerate (D-09): on first detection, signal `generate` to retry once with a "remove the prescriptive language" addendum. On second detection, refuse. Counter lives in `GraphState.regenerate_attempts`.

`compliance/disclaimer_text.py` is the single source of truth for the anchor copy (D-07). All three disclaimer surfaces import from here.

### F. The Renderer Contract

The LLM emits `{{claim_id}}` placeholders inside `answer_prose`. The renderer in `ui/citation_chip.py` (Wave 4) walks the prose, finds placeholders, deduplicates per-cluster (D-03), assigns per-answer numbers `[1] [2] [3]` (resets per answer — D-01), and emits the HTML contract from UI-SPEC Visuals:

```html
<sup class="drhp-cite" data-claim-id="c_4f3a"
     tabindex="0" role="button" aria-describedby="cite-1-source">[1]</sup>
```

The LLM NEVER writes `(p.142)` in prose. This is how PITFALL P5 (citation drift) is structurally eliminated.

### G. Project Directory Layout

Locked at end of Wave 0. Phases 2-6 add files inside these folders; they do not reorganize:

```
drhplens/
├── app.py
├── pyproject.toml
├── requirements.txt
├── README.md                       # HF Spaces YAML frontmatter
├── pages/01_methodology.py         # Phase 1 stub; Phase 6 LAND-01 fills
├── agent/{graph.py, state.py, schemas.py, nodes/, prompts/}
├── pipelines/{ingest_swiggy.py, verify_index.py}
├── tools/{embedder.py, reranker.py}
├── storage/vector.py
├── ui/{chat.py, citation_chip.py, disclaimer.py, refusal_banner.py, copy.py}
├── compliance/{banned_tokens.py, disclaimer_text.py}
├── observability/langfuse_setup.py
├── data/swiggy_drhp/{*.pdf, *.docling.json, SHA256SUMS}
├── static/drhplens.css
└── tests/{unit, integration, eval}
```

---

## What the Skeleton Does NOT Include

These are deliberate deferrals to keep Wave 3 small enough to ship:

- **No Streamlit UI.** That's Wave 4.
- **No HF Spaces deployment.** That's Wave 5.
- **No Langfuse instrumentation.** That's Wave 5 (the trace shape is decided in skeleton, but the wiring is Wave 5).
- **No first-use modal, no citation chips, no /methodology stub page.** Wave 4.
- **No BM25 hybrid retrieval.** Dense-only is acceptable for Walking Skeleton (PITFALL P20 prevention). Phase 2 may add hybrid if recall < 0.85 on the gold set.
- **No structured-table sidecar.** Tables-as-text in chunks is sufficient for Phase 1 (PITFALL P20). Phase 3 may introduce a `query_financials` tool.
- **No multi-IPO support exposed.** But `drhp_id` is a foreign key on every chunk payload row — Phase 2 just adds more rows.
- **No empty/loading/error UI states.** Wave 4 (after deploy decision UX shapes them).

---

## How the Skeleton Survives Phase 2-6

| Phase | What it adds | What stays unchanged |
|-------|-------------|----------------------|
| 2 | Multi-IPO catalogue, RHP cover-page extraction, BM25 hybrid retrieval (if needed) | Schemas, cite-check, banned-token scrubber, LangGraph topology |
| 3 | Structured red-flag extraction, `query_financials` tool, METHOD-01 "Show your work" pane | Schemas (claim_id is what the pane consumes), cite-check |
| 4 | Historical IPO SQLite DB, peer comparator, GMP scraper read-only | Schemas, cite-check (now also runs over peer-data claims via same algorithm) |
| 5 | XGBoost+MAPIE forecaster, model card, `available_at` feature gating | Schemas, cite-check, scrubber (forecast UI text passes scrubber identically) |
| 6 | Langfuse dashboards inline, LAND-01 recruiter page, FAILGAL-01 failure gallery, supervisor agent topology | Phase 1's claim_id schema is the trace data structure these consume |

The skeleton is built so Phase 6's full surface can ship without touching the schemas. If a Phase N change requires editing `agent/schemas.py`, treat it as a Phase 1 protocol break and discuss before merging.

---

## Skeleton-Ship Checklist (Wave 3 close)

- [ ] `data/swiggy_drhp/swiggy_prospectus_2024_11.pdf` committed; SHA-256 pin matches
- [ ] `data/swiggy_drhp/swiggy_prospectus_2024_11.docling.json` committed (~10-30 MB)
- [ ] Qdrant Cloud `drhp_chunks` collection has 1500-2500 chunks for `drhp_id=swiggy_2024_11`
- [ ] `pytest tests/unit -x -q` passes (< 10 sec)
- [ ] `pytest tests/integration -x -q --timeout=60` passes (mocked Qdrant + LLM)
- [ ] `python -m agent.demo "What is Swiggy's issue size?"` returns a `GroundedAnswer` with ≥ 1 claim, every claim cite-checked
- [ ] `python -m agent.demo "What does Swiggy say about Mars colonization?"` returns a `RefusalResponse` with reason `low_retrieval_score` and ≥ 1 reformulation suggestion
- [ ] `python -m agent.demo "Should I subscribe to Swiggy?"` returns a `RefusalResponse` with reason `banned_token` after exhausting the regenerate-once budget
- [ ] `agent/schemas.py` lines load-bearing; signed off by checker as the Phase 3 METHOD-01 contract

When all checkboxes pass, the skeleton is live and Wave 4 (UI) is unblocked.

---

*Walking Skeleton spec for Phase 1*
*Authored alongside PLAN files: 2026-05-28*
*Subsequent phases inherit Sections A-G unchanged.*
