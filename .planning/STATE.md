---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
last_updated: "2026-06-24T07:48:09.273Z"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 11
  completed_plans: 9
  percent: 17
---

# STATE: DRHPLens

**Last Updated:** 2026-06-23

## Project Reference

**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

**Project Mode:** MVP (vertical-slice progression)

**Audience:** Indian retail investors (mobile-first); secondary audience is the DS-recruiter reviewing the portfolio piece.

**Current Focus:** Phase 2 — Multi-IPO Catalogue + DRHP Snapshot Surface (Wave 1 complete: drhp_id threading + catalogue allow-list + 8-IPO catalogue.json).

## Current Position

**Phase:** 2 of 6 — Multi-IPO Catalogue + DRHP Snapshot Surface
**Plan:** 02-02 of 02-05 complete (Wave 1: drhp_id threading + catalogue loader/allow-list + 8-IPO catalogue)
**Status:** Phase complete — ready for verification
**Progress:** [████████░░] 82%

## Phase Map

| Phase | Name | Status |
|-------|------|--------|
| 1 | Foundation + MVP-A (Cited Q&A on One IPO) | Complete |
| 2 | Multi-IPO Catalogue + DRHP Snapshot Surface | In progress (Wave 1 of plans 02-01..02-05 done) |
| 3 | Structured Signal Extraction (Red-Flag Table) | Not started |
| 4 | Historical IPO Dataset + Peer Comparator + GMP Display | Not started |
| 5 | Calibrated Listing-Day Forecaster | Not started |
| 6 | Full Eval Harness + Agentic Polish + Portfolio Surface | Not started |

## Performance Metrics

(Populated as phases complete.)

- Phases completed: 0 / 6
- v1 requirements satisfied: 0 / 42
- Numeric faithfulness (release gate >=0.95): not yet measured
- Citation accuracy (release gate >=0.95): not yet measured
- Forecast empirical coverage (target 80%): not yet measured

## Accumulated Context

### Key Decisions (from PROJECT.md)

- India-focused (not US) — personal credibility + underserved market + differentiation
- IPO/DRHP decoder as v1 (vs earnings analyst) — most distinctive RAG showcase
- Honesty-first framing — cited, calibrated, not-advice (compliance + differentiator)
- Hybrid agentic architecture — RAG + NLP extraction + peer-comparison + historical-IPO forecasting
- v2 evolution toward Portfolio Red-Flag Radar SaaS

### Key Decisions (from research)

- Stack locked: LangGraph + LlamaIndex + Docling + Qdrant + BAAI/bge-m3 + XGBoost + MAPIE + RAGAS/DeepEval/Langfuse + Streamlit on HF Spaces
- Frontend: Streamlit for Phases 1-5; explicit re-evaluation gate at Phase 5 exit before considering Next.js migration
- GMP: display read-only, computationally isolated from forecast model — gap between GMP and GMP-free model output is the honest signal
- Agent: bounded LangGraph state machine (not freeform ReAct); cite-check is a deterministic code node
- Storage is the integration bus — batch pipelines write, on-demand tools read

### Key Decisions (from Wave 1)

- claim_id pattern `^c_[a-z0-9]{6,16}$` locked in SKELETON §B (changing it breaks Phase 3 METHOD-01)
- Morphological stems (subscri, accumulat) used in BANNED_TOKEN_PATTERN because Python literal matching cannot handle e-dropping in subscribe→subscribing
- ANCHOR_COPY D-07 byte-for-byte in compliance/disclaimer_text.py — single source of truth
- Import-time scrubber assertion in ui/copy.py is the TRUST-03 anchor (fails fast on banned-token regressions in our own copy)
- REFUSAL_BANNED_TOKEN_COPY reworded to avoid "recommendation" which the scrubber correctly blocked

### Cross-Cutting Invariants (from PITFALLS.md)

- Compliance posture hardcoded from Phase 1 (disclaimer + banned-token scrubber + no-personalization)
- Span-level citations from day one (not page-level); non-LLM cite-check node validates before emit
- Numeric-faithfulness >=0.95 release gate from Phase 3 onward
- Survivorship-corrected universe (SEBI-issuer-side sourced + status column)
- All forecast features carry `available_at` timestamp; walk-forward CV only
- >=35-40% non-LLM modeling time budget (cut agent scope before cutting modeling scope)
- Four baselines reported alongside every model
- GMP display !== GMP feature

### Open TODOs

- Run `/gsd-plan-phase 1` to begin Phase 1 detailed planning
- Hand-pick the single "MVP-A" IPO for Phase 1 (recent mainboard listing with a clean DRHP)
- Curate the 5-10 IPO catalogue for Phase 2 ahead of Phase 1 exit
- Begin hand-labeling extraction gold set (20-30 DRHPs) during Phase 2 (concurrent prep for Phase 3)
- Begin EDA notebooks for forecaster feature set during Phase 4 (concurrent prep for Phase 5)
- Schedule SEBI legal-review checkpoint before Phase 6 public launch

### Key Decisions (from Phase 2 Wave 1 / 02-02)

- drhp_id defaults via intake.run (`state.get('drhp_id') or DRHP_ID_DEFAULT`) to preserve every Phase 1 call shape
- V5 allow-list guard (is_known_drhp_id) lives inside retrieve.run, before search() — co-located with the boundary it protects
- catalogue.json holds catalogue-level metadata only; no fabricated financials; source_sha256 stays null until Wave 2 ingest pins it per IPO

### Open Blockers

None yet.

## Research Flags (from ROADMAP.md)

- **Phase 4 start:** `jugaad-data` endpoint validation spike (~1 day) + nightly integration test setup
- **Phase 5 start:** ~1 week of EDA notebooks on India-IPO feature engineering before committing to the feature set
- **Phase 6 start:** Brief exploration spike on DeepEval CI integration + Langfuse custom-score callbacks (~1-2 days)

## Session Continuity

### What I Was Doing

Phase 2 Plan 02-02 (Wave 1) complete: threaded drhp_id through GraphState -> intake -> retrieve -> refuse_with_reformulation with a back-compat-preserving default; shipped data/catalogue_loader.py (Pydantic CatalogueIPO model + load_catalogue() + is_known_drhp_id() V5 allow-list); filled data/catalogue.json with all 8 curated IPOs. 3 xfail stubs flipped to 11 real passing tests. 237 unit tests passing (226 baseline + 11 new), 6 xfail remaining (Wave 2/3 stubs), 1 pre-existing ignorable embedder failure (missing sentence-transformers).

### Where to Resume

Execute Plan 02-03 (Wave 2): ingest generalization — pipelines/ingest_swiggy.py -> pipelines/ingest.py(drhp_id, pdf_path) parameterized, looped over data/catalogue.json's 8 entries. Requires live Qdrant + bge-m3/torch for the actual multi-IPO ingest (deferred dependency from Phase 1's INGEST_LATER.md).

### Files of Record

- `.planning/PROJECT.md` — project context and constraints
- `.planning/REQUIREMENTS.md` — 42 v1 requirements with phase mappings
- `.planning/ROADMAP.md` — 6-phase vertical-slice roadmap
- `.planning/research/SUMMARY.md` — research synthesis (start here)
- `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md` — dimension files
- `.planning/config.json` — granularity=standard, parallelization=true, model_profile=quality

---
*State initialized: 2026-05-28*

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 01 P01 | 25min | 3 tasks | 48 files |
| Phase 01 P02 | 45min | 3 tasks | 11 files; 108 unit tests passing |
