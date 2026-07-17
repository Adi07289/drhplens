---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-07-16T18:36:10.917Z"
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 36
  completed_plans: 26
  percent: 50
---

# STATE: DRHPLens

**Last Updated:** 2026-07-17

## Project Reference

**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

**Project Mode:** MVP (vertical-slice progression)

**Audience:** Indian retail investors (mobile-first); secondary audience is the DS-recruiter reviewing the portfolio piece.

**Current Focus:** Phase 05 — calibrated-listing-day-forecaster

## Current Position

Phase: 05 (calibrated-listing-day-forecaster) — EXECUTING
Plan: 4 of 11
**Status:** Ready to execute
**Progress:** [███████░░░] 72%

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

- **[04-07 live build — BLOCKED on source rot, DEFERRED to Phase 5 start]** Phase 4 is **6/7 code-complete** (04-01…04-06 done, all user-facing surfaces shipped + 375px-approved). The 04-07 full historical panel build fails at the universe step: `chittorgarh` migrated to a Next.js app, so `pipelines/historical/sources.py::fetch_chittorgarh_index` (`soup.find("table")`) returns 0 rows from BOTH Colab and a local residential IP (confirmed NOT an IP block). The offline SAMPLE + schema + validator + unit tests stay green; nothing user-facing depends on the real panel (it is Phase 5's foundation). **Fix documented in `data/historical/README.md`** (rewrite to chittorgarh's `webnodejs …/data-read/83/…` JSON API — endpoint confirmed live, params need reverse-engineering — or switch to an NSE/BSE/SEBI universe source). Do this when Phase 5 first needs the panel.

## Research Flags (from ROADMAP.md)

- **Phase 4 start:** `jugaad-data` endpoint validation spike (~1 day) + nightly integration test setup
- **Phase 5 start:** ~1 week of EDA notebooks on India-IPO feature engineering before committing to the feature set
- **Phase 6 start:** Brief exploration spike on DeepEval CI integration + Langfuse custom-score callbacks (~1-2 days)

## Session Continuity

### What I Was Doing

Executed Phase 5 Plan 05-03 (Wave 2, the cache-only contract — D5-11 / FCAST-02 isolation) — defined the `ForecastRecord` schema and the allow-list-gated `load_forecast(drhp_id)` reader that together form the single seam between the offline forecaster and the cache-only Streamlit render. Task 1 `7fe818e` (feat): `agent/forecast_schema.py` — a flat, import-light (pydantic + stdlib only) `ForecastRecord` with nested `ForecastInterval` (low/high/median/width) + GLOBAL `ForecastMetrics` (coverage/mae/backtest_window/n/per_year_rmse), covered/abstain as first-class states (interval None on abstain, no fabricated numbers), `is_abstain` property, `median_pct` kept a plain field (P21), and a `to_dict/to_json(indent=2, ensure_ascii=False)/from_dict/from_json` codec that parses the two committed `data/forecasts/*.json` seeds byte-for-byte; `tests/unit/test_forecast_schema.py` (7 tests: round-trip + covered/abstain + import-audit). Task 2 `0d90ebd` (feat): `pipelines/forecast/__init__.py` — `load_forecast` gates `drhp_id` via `is_known_drhp_id` BEFORE forming any `data/forecasts/<id>.json` path (T-05-03-PATH), returns a `ForecastRecord`, raises `FileNotFoundError` on a missing file (the render's honest not-covered state); `FORECASTS_DIR` uses `resolve().parents[2]` (the plan's literal `.parent.parent` would resolve to `pipelines/data/forecasts` — Rule 1 fix). `tests/unit/test_forecast_isolation.py` — the two-direction `inspect.getsource` audit mirroring `test_gmp_isolation.py` (render imports no model; predictor/loader/record imports no display signal; not-yet-built 05-05/05-07 modules `importorskip`-guarded), plus unknown-id `ValueError` + committed-seed reads + missing-file `FileNotFoundError` (11 tests, 4 skipped). Suite: 390 passed, 4 skipped, 1 pre-existing ignorable embedder failure (sentence-transformers not installed — unrelated).

### Where to Resume

Phase 5 Wave 2 cache-only contract (05-03) COMPLETE — the `ForecastRecord` schema + the allow-list-gated `load_forecast` reader + the two-direction isolation audit are in place, offline-green, and parse the two 05-01 committed seeds verbatim. This unblocks the render slice (05-07) and the precompute writer (05-06) to proceed in parallel against the fixtures. **FCAST-02 remains Pending** — 05-03 delivers only the isolation clause ("no display signal", pinned both directions) + the cache seam; the `available_at` feature-leakage half lands in 05-04/05-05 and the render half in 05-07 (do not close FCAST-02 yet). FCAST-03 also stays **Pending** (walk-forward CV half still open). Next: execute the remaining Wave 2+ modeling slices — 05-04 features (`available_at` no-leakage gate) / 05-05 CQR + walk-forward / metrics / baselines, then 05-06 precompute writer + 05-07 render. The isolation test will auto-execute its real render/model audit once `ui.forecast_block` (05-07) and `pipelines.forecast.model`/`walkforward`/`pipelines.features` (05-05) land (currently `importorskip`-skipped). Carry-overs that do NOT block Phase 5 code: (1) the 03-05 live `make release` numeric-gate (human-only); (2) the real historical-panel build is now a 05-11 checkpoint step (the 05-01 synthetic fixture unblocks the tests until then); the nightly canary watches the NSE past-issues endpoint for drift.

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
| Phase 04 P03 | 40min | 3 tasks | 8 files |
| Phase 04 P04 | 20min | 2 tasks | 8 files |
| Phase 05 P01 | ~40 min | 2 tasks | 6 files |
| Phase Phase 05 PP02 | ~15 min | 2 tasks tasks | 5 files files |
| Phase 05 P05-03 | ~20 min | 2 tasks | 4 files |

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
- [Phase ?]: [Phase 04 / 04-03]: PeerCell adds a not_meaningful boolean so a negative/undefined P/E renders NM (value None), distinct from a missing '—' cell; peer_set reuses the {refusal} discriminator codec verbatim from redflag_schema (D4-06 empty-state)
- [Phase ?]: [Phase 04 / 04-03]: peer multiples ladder screener(s)->yfinance(y)->NSE(n) first-available per cell; 0/None/NaN->missing (P15), yfinance ROE fraction x100 as percent, rapidfuzz name->ticker allow-list keeps SSRF hosts hard-coded; live scrape + DRHP-date extraction deferred (CODE-NOW-DEFER, seed unblocks 04-05)
- [Phase 05]: numpy stepped 2.4.6->2.3.5 (still 2.x) so shap imports (shap->numba hard-caps numpy<2.4; no numba supports 2.4); pandas KEPT at 3.0.3 (mlflow pandas<3 is soft, imports fine). Resolved: xgboost 3.2.0/mapie 1.4.1/sklearn 1.9.0/mlflow 3.14.0/matplotlib 3.11.0/shap 0.51.0; libomp installed for xgboost OpenMP.
- [Phase 05]: data/forecasts/{swiggy_2024_11,hyundai_2024_10}.json are hand-seeded ForecastRecords (full-render + abstain) to unblock the render slice offline; regenerated from the real walk-forward run in 05-06/05-11 (Phase 4 GMP CODE-NOW-DEFER seed posture).
- [Phase 05]: Phase 05 / 05-02: FCAST-03 left Pending — it spans 5 Phase-5 plans and requires walk-forward CV; 05-02 delivers only the survivorship-universe half (NSE past-issues + SEBI/chittorgarh-withdrawn two-source merge, deduped by issuer+issue_date, listed-core wins collisions). chittorgarh HTML scraper demoted from primary (D5-04); nse lib optional/lazy, gated to 05-11.
- [Phase ?]: [Phase 05 / 05-03]: FORECASTS_DIR uses Path(__file__).resolve().parents[2] (repo-root data/forecasts), not the plan's literal .parent.parent which would resolve to pipelines/data/forecasts — the loader __init__ sits one level deeper than pipelines/gmp.py (Rule 1 fix, matches RESEARCH sketch).
- [Phase ?]: [Phase 05 / 05-03]: FCAST-02 isolation pinned in BOTH directions via inspect.getsource — render (ui.forecast_block + snapshot page) imports no model; predictor (loader + record + model/feature modules) imports no display signal. Not-yet-built 05-05/05-07 modules importorskip-guarded so the audit is green today and auto-runs the real check when they land.
- [Phase ?]: [Phase 05 / 05-03]: FCAST-02 left Pending — 05-03 delivers the isolation clause + cache seam; the available_at feature-leakage half is 05-04/05-05 and the render half 05-07 (mirrors 05-02 leaving FCAST-03 open). Schema+loader avoid the literal substrings 'shap'/'gmp' in their own source so the token audit stays green ('shape'->'shap' gotcha).
