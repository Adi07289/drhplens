---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-06-25T18:23:29.580Z"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 18
  completed_plans: 16
  percent: 33
---

# STATE: DRHPLens

**Last Updated:** 2026-06-23

## Project Reference

**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

**Project Mode:** MVP (vertical-slice progression)

**Audience:** Indian retail investors (mobile-first); secondary audience is the DS-recruiter reviewing the portfolio piece.

**Current Focus:** Phase 03 — Structured Signal Extraction (Red-Flag Table)

## Current Position

Phase: 03 (Structured Signal Extraction (Red-Flag Table)) — EXECUTING
Plan: 4 of 7 complete (Wave 4: EXTRACT-03 gold-set F1 scorer + labeling rubric)
**Status:** Executing Phase 03
**Progress:** [█████████░] 89%

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

- **[03-05 Task 3 — blocking checkpoint]** Live `make release` numeric-gate run is PENDING. Needs `GEMINI_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` + swiggy_2024_11 ingested into live Qdrant. The gate logic is CI-tested offline (0.94 fails / 0.95 / 0.96 pass); only the live verification remains. EVAL-03 stays open until verified.

## Research Flags (from ROADMAP.md)

- **Phase 4 start:** `jugaad-data` endpoint validation spike (~1 day) + nightly integration test setup
- **Phase 5 start:** ~1 week of EDA notebooks on India-IPO feature engineering before committing to the feature set
- **Phase 6 start:** Brief exploration spike on DeepEval CI integration + Langfuse custom-score callbacks (~1-2 days)

## Session Continuity

### What I Was Doing

Phase 3 Plan 03-05 (Wave 4) AUTONOMOUS WORK complete; LIVE checkpoint PENDING. Created eval/gold/numeric_eval.jsonl — 50 Swiggy-anchored numeric-only Qs, each with arithmetically-correct gold_numeric + gold_unit + source_page (D3-11); lakh/crore conversions use 1 crore = 100 lakh (11,327.43 cr = 11,32,743 lakh), explicitly avoiding the off-by-10x 1,12,470-lakh figure in 03-RESEARCH/03-PATTERNS; fresh/OFS use real Swiggy figures (4,499 cr / 6,828.43 cr) not the snapshot's 59/41 placeholder. Extended scripts/run_eval.py additively with compute_numeric_faithfulness (reuses agent.nodes.cite_check per-number grounding; importable by the gate; dated numeric-track report) — Phase 1 track untouched. Created scripts/release_gate.py — pure enforce_gate(score) reads NUMERIC_FAITHFULNESS_GATE from policy, writes dated *-numeric-gate.md report + sys.exit(1) below threshold, passes at/above (>= boundary); main() owns the only live call. Created Makefile release: target (Make halts on non-zero exit). Flipped tests/eval/test_release_gate.py skip->green (0.94 fails+reports / 0.95 / 0.96 pass), fully offline. 292 passed, 1 pre-existing ignorable embedder failure. Commits 1c6f927 (feat), 561b06e (test RED), d5db2a4 (feat GREEN).

### Where to Resume

BLOCKING CHECKPOINT — Plan 03-05 Task 3 (live `make release`) is PENDING and requires live services. Run `make release` against live Qdrant+Gemini with swiggy_2024_11 ingested; confirm it exits non-zero below 0.95 (writing eval/reports/<date>-numeric-gate.md) or prints OK at >=0.95; commit the report; then mark EVAL-03 complete and close 03-05 via `gsd-sdk query roadmap.update-plan-progress 03 03-05 complete`. Only after that, execute Plan 03-04 (extraction-F1 eval harness) and Plans 06/07 (UI render of fields + ranked_risks + methodology pane).

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
| Phase 02 P04 | 50m | 2 tasks | 9 files |
| Phase 02 P05 | 70min | 2 tasks | 8 files |
| Phase 03 P03 | 22min | 2 tasks | 5 files; 290 unit tests passing |
| Phase 03 P05 | ~25min | 2 of 3 tasks (Task 3 live checkpoint pending) | 5 files; 292 passed; numeric gate offline-green |
| Phase 03 P04 | 12min | 2 tasks | 5 files |

## Decisions

- [Phase ?]: compute_ofs_fresh uses percent-to-keyword proximity matching for robust OFS/fresh parsing
- [Phase ?]: swiggy_2024_11.json snapshot seeded by hand (CODE-NOW placeholder), numerically self-consistent, flagged for live regeneration via the runbook
- [Phase 02]: Split-bar caption reworded to avoid scrubber sell-stem collision (shares offered by existing shareholders)
- [Phase 02]: render_snapshot_chat extracted into ui/snapshot_chat.py so pages/02_snapshot.py does not import app.py
- [Phase 03]: a numeric-gate-blocked red-flag field maps to RefusalResponse(reason=unsupported_claim, explanation=L3-9 copy) — no new RefusalReason literal; the explanation carries the verbatim blocked-copy the renderer needs
- [Phase 03]: ofs_vs_fresh reuse surfaces the snapshot's already-vetted use_of_proceeds GroundedAnswer without re-scrubbing (the snapshot pipeline already scrubbed + cite-checked it) — re-gating defeats reuse
- [Phase 03]: in-corpus IDF is phrase-level (3-5 word shingles, not unigram); boilerplate floor is a deterministic small-n IDF-noise clamp; stdlib + rapidfuzz only, no sklearn
- [Phase ?]: EXTRACT-03 gold set is honest-n (1 ingested DRHP, 7 cells); end-to-end F1 run over cached records deferred-to-live
