---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-07-05T20:25:38.105Z"
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 18
  completed_plans: 18
  percent: 50
---

# STATE: DRHPLens

**Last Updated:** 2026-07-06

## Project Reference

**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

**Project Mode:** MVP (vertical-slice progression)

**Audience:** Indian retail investors (mobile-first); secondary audience is the DS-recruiter reviewing the portfolio piece.

**Current Focus:** Phase 03 — Structured Signal Extraction (Red-Flag Table)

## Current Position

Phase: 03 (Structured Signal Extraction (Red-Flag Table)) — CODE WORK COMPLETE (7 of 7 plans)
Plan: 7 of 7 complete (Wave 5: 03-07 — red-flag table + single IDF risk list + methodology pane wired into pages/02_snapshot.py; Task 3 375px human-verify checkpoint APPROVED)
**Status:** Phase 3 code work done; ONE human-only item pending (03-05 live `make release` numeric-gate — needs GEMINI_API_KEY + live Qdrant with the gold-set ingested; does NOT block code completion)
**Progress:** [██████████] 100%

## Phase Map

| Phase | Name | Status |
|-------|------|--------|
| 1 | Foundation + MVP-A (Cited Q&A on One IPO) | Complete |
| 2 | Multi-IPO Catalogue + DRHP Snapshot Surface | Complete |
| 3 | Structured Signal Extraction (Red-Flag Table) | Code complete (7/7 plans; 03-05 live numeric-gate pending) |
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

### Key Decisions (from Phase 3 Wave 4 / 03-06)

- Methodology pane (`ui/methodology_pane.py`) is a cached-only render — the numeric confidence score (0.00-1.00) surfaces ONLY inside the Show-your-work expander (D3-02/L3-2), never in the up-front row
- The pane reuses `ui.expander.render_citation_expanders` for the escaped Sources-cited `metadata_footer` and reads chunk scores directly from the cached `GroundedAnswer.claims[].sources[].score` (the descriptor omits score)
- No live LLM/Qdrant call on expand (Pitfall 5 / D3-17), pinned by an `inspect.getsource` no-client substring gate (`test_no_llm_or_qdrant_import`)
- `latest_eval_scores` picks the newest `eval/reports/*.md` by ISO-date-prefixed filename (lexical == chronological) and degrades to `None` → eval-not-available copy on a missing/empty report dir

### Open Blockers

- **[03-05 Task 3 — human-only, does NOT block code completion]** Live `make release` numeric-gate run is PENDING on the user's environment. Needs `GEMINI_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` + swiggy_2024_11 ingested into live Qdrant. The gate logic is CI-tested offline (0.94 fails / 0.95 / 0.96 pass); only the live verification remains. EVAL-03 stays open until verified. This is the ONE outstanding Phase 3 item — the phase's CODE work is complete (7/7 plans).

## Research Flags (from ROADMAP.md)

- **Phase 4 start:** `jugaad-data` endpoint validation spike (~1 day) + nightly integration test setup
- **Phase 5 start:** ~1 week of EDA notebooks on India-IPO feature engineering before committing to the feature set
- **Phase 6 start:** Brief exploration spike on DeepEval CI integration + Langfuse custom-score callbacks (~1-2 days)

## Session Continuity

### What I Was Doing

Closed out Phase 3 Plan 03-07 (Wave 5) — the Phase 3 UI payoff. The red-flag signals table (7 stacked monochrome rows in canonical order, tabular-nums chip-rendered values, neutral Confidence:{tier} text, honest Not-disclosed rows with confidence omitted, numeric-gate blocked-copy — no red/green, no badges), the SINGLE IDF-ranked risk list with the monochrome specificity meter (superseding the Phase 2 prioritized ordering), and the cached-only Show-your-work methodology pane are wired into pages/02_snapshot.py + ui/snapshot_chat.py, all reading the committed RedFlagRecord cache with zero request-time LLM calls. Task 1 `40df830` (render_redflag_table + render_idf_risk_list in ui/snapshot_blocks.py), Task 2 `5586df9` (page wiring + Q&A pane), Task 3 checkpoint:human-verify (375px mobile visual) — human ran the seeded app and APPROVED. Two live-discovered refinements landed after the plan body: `274a02e` (investor-first two-tier methodology pane — plain-English source verification by default, developer internals behind an off-by-default Show-technical-details toggle) and `c8e301b` (runtime-only fix: red-flag card wrapper switched from a split-div to st.container(border=True) to stop the empty white-bar render, plus unique per-element keys to kill a StreamlitDuplicateElementId crash — both unobservable to the offline executor which cannot run Streamlit). Suite: 303 passed, 1 pre-existing ignorable embedder failure.

### Where to Resume

Phase 3 CODE WORK IS COMPLETE (7/7 plans). The ONLY outstanding Phase 3 item is human-only and does NOT block code completion: run the 03-05 live `make release` numeric-faithfulness gate against live Qdrant+Gemini with swiggy_2024_11 (numeric gold-set) ingested — confirm it exits non-zero below 0.95 (writing eval/reports/<date>-numeric-gate.md) or prints OK at >=0.95, commit the report, then mark EVAL-03 complete. After that live gate, Phase 3 is fully closed and Phase 4 (Historical IPO Dataset + Peer Comparator + GMP) planning can begin (start with the `jugaad-data` endpoint validation spike).

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
| Phase 03 P07 | ~40min + human-verify | 3 tasks (Task 3 375px human-verify APPROVED) | 6 files; 303 passed; red-flag table + single IDF list + panes wired into the snapshot page |

## Decisions

- [Phase ?]: compute_ofs_fresh uses percent-to-keyword proximity matching for robust OFS/fresh parsing
- [Phase ?]: swiggy_2024_11.json snapshot seeded by hand (CODE-NOW placeholder), numerically self-consistent, flagged for live regeneration via the runbook
- [Phase 02]: Split-bar caption reworded to avoid scrubber sell-stem collision (shares offered by existing shareholders)
- [Phase 02]: render_snapshot_chat extracted into ui/snapshot_chat.py so pages/02_snapshot.py does not import app.py
- [Phase 03]: a numeric-gate-blocked red-flag field maps to RefusalResponse(reason=unsupported_claim, explanation=L3-9 copy) — no new RefusalReason literal; the explanation carries the verbatim blocked-copy the renderer needs
- [Phase 03]: ofs_vs_fresh reuse surfaces the snapshot's already-vetted use_of_proceeds GroundedAnswer without re-scrubbing (the snapshot pipeline already scrubbed + cite-checked it) — re-gating defeats reuse
- [Phase 03]: in-corpus IDF is phrase-level (3-5 word shingles, not unigram); boilerplate floor is a deterministic small-n IDF-noise clamp; stdlib + rapidfuzz only, no sklearn
- [Phase ?]: EXTRACT-03 gold set is honest-n (1 ingested DRHP, 7 cells); end-to-end F1 run over cached records deferred-to-live
- [Phase 03 / 03-07]: Plan 03-07 complete — the Phase 3 headline surfaces (red-flag table, single IDF risk list, methodology pane) are wired into pages/02_snapshot.py; Phase 3 code work is DONE (7/7 plans). The Task 3 375px mobile visual checkpoint was human-APPROVED.
- [Phase 03 / 03-07]: The snapshot risk list is reconciled to ONE list — render_idf_risk_list (IDF-ranked, specificity meter) supersedes the Phase 2 render_risk_block ordering; render_risk_block fires only in the empty-ranked_risks else-branch (fallback), never two competing lists
- [Phase 03 / 03-07]: Methodology pane is two-tier and investor-first — plain-English source verification (DRHP page + verbatim quote blockquote + one-line trust sentence with the committed citation-accuracy %) is the default; developer internals (query, chunk scores, prompt, raw eval report, numeric confidence score) sit behind an off-by-default "Show technical details" toggle
- [Phase 03 / 03-07]: Streamlit runtime lesson — a styled card wrapper must be a single st.container(border=True); a div split across two st.markdown calls renders empty (white bar). Every methodology-pane toggle needs a unique per-element key to avoid StreamlitDuplicateElementId. Both were live-only defects surfaced by the human-verify checkpoint (offline executor can't run Streamlit)
