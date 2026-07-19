---
phase: 05-calibrated-listing-day-forecaster
plan: 08
subsystem: infra
tags: [features, available-at, leakage-gate, regime, drhp-derived, anchor, walk-forward, feature-selection, xgboost, sector-pooling, out-of-support, fcast-02, d5-06, d5-07, d5-08, d5-10, honesty]

# Dependency graph
requires:
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-04 pipelines.features FEATURE_SPECS thin issue-structure contract + build_features available_at <= T0 LeakageError gate + leakage_audit (the contract this EXTENDS); 05-05 pipelines.forecast.walkforward as-of-T0 pooling + model.make_quantile_models (the fold engine the selector runs importance over); 05-06 precompute consumers of build_features(X); 05-02 pipelines.historical.sources _get/_check_host + lazy jugaad/yfinance fallback posture (the regime fetchers mirror); data.catalogue_loader.is_known_drhp_id allow-list; data/snapshots (Phase 2) + data/redflag (Phase 3) caches (the family-c sources)"
provides:
  - "pipelines.historical.sources.fetch_nifty_history(end_date) + fetch_india_vix(as_of): live-deferred (# pragma: no cover - live only) regime fetchers reusing the jugaad-data -> yfinance -> None + lazy-client + offline-at-import posture; SSRF-safe module-constant index symbols (T-05-08-SSRF)"
  - "pipelines.features FEATURE_SPECS extended to all four D5-06 families (21 candidates): (a) issue structure + (b) market regime + (c) DRHP-derived + (d) anchor demand, each -> (float64, available_at rule); AVAILABLE_AT_PREOPEN (T0-1) token; REGIME/DRHP/ANCHOR feature groups + FEATURE_FAMILY"
  - "pipelines.features.build: expanded build_features (regime density/trailing panel-derived no-lookahead; family-c allow-list-gated DRHP-cache reads; family-d pre-open anchor allocation) behind the same available_at <= T0 gate; anchor_leakage_audit() (D5-08); pool_sectors(min_n=30) -> ('Other'-pooled Series, n_per_sector report) (D5-10); family-tagged leakage_audit"
  - "pipelines.features.select: select_features(panel, X, max_k=15) -> (lean list, importance/stability table) via walk-forward XGBoost gain (no full-sample leak, D5-07); SELECTED_FEATURES committed lean ~10; training_support(X_train) -> per-feature [q01,q99] + is_out_of_support(x_row, support) (the D5-09 out_of_support abstention input)"
  - "tests/unit/test_features_expanded.py + test_feature_selection.py + extended test_features_available_at.py — family b/c/d T0 gate, allow-list-gated cache read, post-open anchor raises, anchor pre-open audit, sector pooling, no-lookahead regime, lean selection + out-of-support"
affects: [05-09, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Four-family candidate pool behind one available_at <= T0 gate: family-aware _resolve_available_at (filing rule = family a/c; AVAILABLE_AT_PREOPEN = T0-1 snapshot for regime b + anchor d) so every feature's resolved availability is data-true AND <= T0"
    - "Panel-derived regime features (ipo_pipeline_density / trailing_listing_gain) computed STRICTLY from prior listings (listing_date < T0_i) — no-lookahead by construction (P4/P6)"
    - "Allow-list-gated DRHP-cache feature read: is_known_drhp_id BEFORE any data/snapshots|data/redflag path is formed (T-05-08-PATH); numbers ONLY from a clean structured `numeric` block + ranked_risks count — NEVER prose-parsed (honesty; the real numeric extraction lands 05-11)"
    - "Anchor pre-open leakage audit (D5-08): anchor_leakage_audit() names the exact pre-open source field + T0-1 disclosure timestamp + verdict and asserts post-open QIB/NII/RII/subscription_at_close can never be a feature (EXCLUDED_FROM_MODEL)"
    - "Small-N sector pooling (D5-10): pool_sectors(min_n=30) maps <min_n + NaN sectors to 'Other' and returns the ORIGINAL n_per_sector so thinness stays visible (never hidden by pooling)"
    - "Walk-forward feature selection (D5-07): per-fold XGBoost gain importances fit ONLY on pre-T0 data (no full-sample importance leak), ranked by mean importance AND cross-fold rank-stability; SELECTED_FEATURES is the committed lean set the production run trains on, regenerated on the live panel at 05-09/05-11 (CODE-NOW-DEFER)"

key-files:
  created:
    - pipelines/features/select.py
    - tests/unit/test_features_expanded.py
    - tests/unit/test_feature_selection.py
  modified:
    - pipelines/historical/sources.py
    - pipelines/features/__init__.py
    - pipelines/features/build.py
    - tests/unit/test_features_available_at.py

key-decisions:
  - "FCAST-02 / FCAST-05 left PENDING (requirements-completed empty) — following the phase's established honesty posture (05-04/05/06 all left their requirements Pending). This plan completes the available_at feature-leakage half for ALL four families, but FCAST-02's render half + real-panel proof still pend (05-11), and FCAST-05 (the committed model card) is 05-10. Closing them now would be dishonest."
  - "DRHP-derived (c) numbers come ONLY from a clean structured `numeric` block + the ranked_risks COUNT (red_flag_count) — the grounded-prose extraction answers are NEVER parsed for numbers. The forward-compatible `numeric` contract is filled by the real Phase-2 financials + Phase-3 numeric extraction at 05-11; everything absent stays NaN-retained (T-05-08-FAB honesty over a fabricated figure)."
  - "Regime AVAILABLE_AT_PREOPEN features resolve to issue_date - 1 (T0-1 EOD snapshot), strictly < T0 — a data-true stamp for a pre-open feature (not the shared issue-structure available_at stamp). ipo_pipeline_density/trailing_listing_gain are panel-derived from PRIOR listings only (no lookahead)."
  - "Anchor family (d) reads from the pre-open anchor allocation ONLY (panel columns today = the CODE-NOW-DEFER seam; the real pre-open anchor source lands 05-11). Post-open QIB/NII/RII/subscription_at_close were already in EXCLUDED_FROM_MODEL (05-04) and are asserted absent by anchor_leakage_audit (D5-08)."
  - "SELECTED_FEATURES is a committed static lean ~10 spanning all four families (asserted subset of FEATURE_COLUMNS) — importable for the production run without executing the walk-forward; select_features regenerates it from the live panel at 05-09/05-11 (mirrors the phase's precompute CODE-NOW-DEFER posture)."
  - "The two panel-derived regime features made the 05-04 bare-panel all-NaN assertion false (they are honestly computed from the panel), so test_features_available_at's bare-panel test was updated to assert the SOURCELESS families are NaN while density/trailing are panel-derived — the plan authorized this test update."

patterns-established:
  - "Family-aware available_at resolver: a per-feature override still wins; else the family's rule (filing vs pre-open T0-1) decides — one gate, four families, every resolved stamp <= T0"
  - "Cache-feature read is allow-list-gated + structured-only: gate the id first, read only clean numeric fields, NaN-retain the rest (never prose-parse a grounded answer into a fabricated feature value)"
  - "select_features + training_support/is_out_of_support are the D5-07 (lean curation) and D5-09 (out_of_support) seams the 05-09 walk-forward + 05-10 model card both consume"

requirements-completed: []

# Metrics
duration: ~26 min
completed: 2026-07-19
---

# Phase 5 Plan 08: Expanded Four-Family Leakage-Gated Feature Pool + Lean Walk-Forward Selection Summary

**Expanded the leakage-gated feature matrix from the 05-04 issue-structure thin slice to all four D5-06 candidate families — market regime (NIFTY/VIX live-deferred fetchers + panel-derived pipeline density / trailing listing gain), DRHP-derived (allow-list-gated Phase-2/Phase-3 cache reads, structured numbers only — never prose-parsed), and anchor-investor demand (pre-open allocation only, with an explicit D5-08 leakage audit) — each stamped `available_at <= T0` behind the same `LeakageError` gate; pooled small-N sectors into 'Other' with an N-per-sector report (D5-10); and curated the 21-candidate pool to a lean ~10 production set via a walk-forward, no-full-sample-leak XGBoost importance/stability selector (D5-07), plus the `is_out_of_support` training-support helper that feeds D5-09 abstention.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-07-19T06:24:00Z
- **Completed:** 2026-07-19T06:49:54Z
- **Tasks:** 3
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments
- **Task 1 — regime family (b) + fetchers.** `pipelines/historical/sources.py` gains `fetch_nifty_history(end_date)` + `fetch_india_vix(as_of)` — live-deferred (`# pragma: no cover - live only`) seams mirroring `fetch_listing_day_close`'s jugaad-data → yfinance → None fallback with lazy clients, offline at import, SSRF-safe module-constant index symbols. `FEATURE_SPECS` gains the D5-06b regime family (`nifty_mom_3m/6m`, `india_vix`, `ipo_pipeline_density`, `trailing_listing_gain`), each keyed to `AVAILABLE_AT_PREOPEN` (T0-1 EOD snapshot ≤ T0); `build._resolve_available_at` became rule-aware so pre-open features resolve to `issue_date - 1` (strictly < T0). P6 regime-shift is now representable.
- **Task 2 — DRHP-derived (c) + anchor (d) + audit + pooling.** `build_features` now derives family (c) from `data/snapshots` (Phase 2) + `data/redflag` (Phase 3) through the `is_known_drhp_id` allow-list gate (path formed only after the gate; numbers ONLY from a clean structured `numeric` block + the `ranked_risks` count → `red_flag_count`, never prose-parsed), family (d) from the pre-open anchor allocation only, and the two panel-derived regime features strictly from PRIOR listings (no lookahead). `anchor_leakage_audit()` names each anchor feature's pre-open source field + T0-1 disclosure timestamp + verdict and asserts the post-open QIB/NII/RII/`subscription_at_close` multiples can never be features (D5-08). `pool_sectors(min_n=30)` maps rare/NaN sectors → 'Other' and returns the original `n_per_sector` report (D5-10). `leakage_audit()` now tags family a/b/c/d.
- **Task 3 — lean selection (D5-07) + out-of-support (D5-09 input).** `pipelines/features/select.py`: `select_features(panel, X, max_k=15)` runs the as-of-T0 walk-forward, collects per-fold XGBoost gain importances (fit ONLY on pre-T0 data — no full-sample importance leak, P4), ranks by mean importance AND cross-fold stability, and returns a lean set + an importance/stability table (the model-card input). `SELECTED_FEATURES` is a committed lean ~10 spanning all four families. `training_support(X_train)` → per-feature `[q01,q99]`; `is_out_of_support(x_row, support)` flags extrapolation — the D5-09 `out_of_support` input the 05-09 walk-forward will consume. xgboost stays lazy (module import offline).

## Task Commits

Each task was committed atomically:

1. **Task 1: Market-regime feature family (b) + regime source fetchers** — `b4848e9` (feat)
2. **Task 2: DRHP-derived (c) + anchor (d) features, anchor leakage audit (D5-08), sector pooling (D5-10)** — `944c698` (feat)
3. **Task 3: Lean feature selection (D5-07) + training-support helper (D5-09 input)** — `90c5801` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

_Note: MVP mode ON / TDD mode OFF per the execution brief — each task's module + its tests were committed together in one atomic `feat` commit (no separate RED/GREEN commits), matching the 05-05/05-06 posture._

## Files Created/Modified
- `pipelines/historical/sources.py` (MODIFIED) — `fetch_nifty_history` + `fetch_india_vix` live-deferred regime fetchers + `NIFTY_INDEX_SYMBOL`/`INDIA_VIX_SYMBOL` constants; added to `__all__`.
- `pipelines/features/__init__.py` (MODIFIED) — `FEATURE_SPECS` extended to all four families (21 candidates); `AVAILABLE_AT_PREOPEN`; `ISSUE_STRUCTURE_FEATURES`/`REGIME_FEATURES`/`DRHP_FEATURES`/`ANCHOR_FEATURES`/`FEATURE_FAMILY`; D5-08 EXCLUDED comment.
- `pipelines/features/build.py` (MODIFIED) — family-aware `_resolve_available_at`; `_read_drhp_numeric`/`_derive_drhp_features` (allow-list-gated cache reads); `_derive_regime_features` (no-lookahead panel derivation); `SNAPSHOTS_DIR`/`REDFLAG_DIR`; `anchor_leakage_audit`; `pool_sectors`; family-tagged `leakage_audit`.
- `pipelines/features/select.py` (NEW) — `select_features` (walk-forward importance/stability), `SELECTED_FEATURES`, `training_support`, `is_out_of_support`; lazy xgboost.
- `tests/unit/test_features_available_at.py` (MODIFIED) — bare-panel test updated for the two panel-derived regime features.
- `tests/unit/test_features_expanded.py` (NEW) — 11 tests: family b/c/d T0 gate, allow-list-gated cache read, post-open anchor raises, anchor audit, sector pooling, no-lookahead regime.
- `tests/unit/test_feature_selection.py` (NEW) — 5 tests: lean set ≤ max_k + table per candidate, out-of-support True/False + missing-not-flagged, SELECTED_FEATURES subset, subprocess lazy-import proof.

## Decisions Made
- **FCAST-02 / FCAST-05 left Pending** (requirements-completed empty) — see key-decisions. This plan delivers the available_at feature-leakage half for all four families; the render half + real-panel proof (05-11) and the model card (05-10) still pend. Consistent with every prior Phase-5 plan.
- **DRHP-derived numbers are structured-only, never prose-parsed** — `red_flag_count` from `len(ranked_risks)` is the one signal cleanly derivable from today's grounded caches; the other 7 family-(c) features read a forward-compatible `numeric` block (filled by real extraction at 05-11) and stay NaN-retained today.
- **Regime pre-open features resolve to T0-1**; density/trailing panel-derived from prior listings only.
- **Anchor reads the pre-open allocation only** (panel-column seam today → real source 05-11); post-open subscription asserted excluded (D5-08).
- **SELECTED_FEATURES is a committed lean ~10**, regenerated by `select_features` on the live panel at 05-09/05-11.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated the 05-04 bare-panel all-NaN assertion for the panel-derived regime features**
- **Found during:** Task 2 (adding the panel-derived regime derivation)
- **Issue:** `test_features_available_at.py::test_build_features_returns_exactly_feature_columns_bare_panel` asserted `x.isna().all().all()` on a bare panel. But `ipo_pipeline_density`/`trailing_listing_gain` are now HONESTLY panel-derived (from prior listings), so a bare panel legitimately produces non-NaN values for them — the blanket assertion was no longer true.
- **Fix:** Narrowed the assertion to the SOURCELESS families (issue-structure a, fetch-based regime nifty/vix, DRHP-derived c, anchor d) staying NaN, plus a positive assertion that the panel-derived density is computed. The plan explicitly authorized updating this test.
- **Files modified:** `tests/unit/test_features_available_at.py`
- **Verification:** `pytest tests/unit/test_features_available_at.py -q` → all pass; the gate/retention/audit invariants are unchanged.
- **Committed in:** `944c698` (Task 2 commit)

**2. [Rule 3 - Blocking] Dropped a non-hermetic "real seed" test that depended on the untracked `data/redflag/` file**
- **Found during:** Task 2 (writing test_features_expanded.py)
- **Issue:** An initial test read the REAL committed `data/redflag/swiggy_2024_11.json` (5 ranked risks) to assert `red_flag_count == 5`. But `data/redflag/` is UNTRACKED in this working tree (and must stay untouched per the execution brief), so the test would be non-hermetic / fail on a fresh checkout.
- **Fix:** Removed that test; the monkeypatched-tmp-cache test already proves `red_flag_count` derives from the `ranked_risks` structured count without depending on any committed cache.
- **Files modified:** `tests/unit/test_features_expanded.py`
- **Verification:** The family-(c) cache-read test uses a tmp-dir fixture via `monkeypatch.setattr(build.SNAPSHOTS_DIR/REDFLAG_DIR)` — fully hermetic.
- **Committed in:** `944c698` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug — a stale test assertion invalidated by the new honest derivation; 1 blocking — a non-hermetic test-data dependency). **Impact on plan:** Both strengthen honesty/hermeticity and were necessary to keep the suite green + reproducible. No scope creep; no new dependencies; the module surface matches the plan's `must_haves.artifacts` and `key_links`.

## Issues Encountered
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` still fails (`sentence-transformers is not installed`) — the documented ignorable embedder failure, unrelated to this plan. Not a regression: the suite went 442 → 455 passed (+13 new tests: 8 expanded/available-at + 5 selection), 0 skipped, same single embedder failure throughout. The 05-03 two-direction isolation audit (11 tests incl. `pipelines.features`) stays green — the expanded feature layer references no display signal and imports no modelling library at module load.

## User Setup Required
None — no external service configuration required. The feature layer is offline-only (regime fetchers are live-deferred `# pragma: no cover - live only` seams proven via the offline fixtures + lazy clients; family-c cache reads are hermetic via tmp-dir monkeypatch; xgboost/jugaad-data/yfinance already installed). The real regime/anchor values + real DRHP numeric extraction + the live feature-selection run land at the deferred **05-11** checkpoint.

## Next Phase Readiness
- The full four-family leakage-gated candidate pool (21 features) + the lean `SELECTED_FEATURES` set + the `is_out_of_support` helper are built, offline-green, and importable on the same `build_features(panel) -> (X, available_at)` contract 05-05/05-06 consume. **05-09** (four baselines + Diebold–Mariano release gate + `min_train`/`cal_frac` tuning) can run over the expanded pool and wire `is_out_of_support` into the walk-forward's D5-09 abstention; **05-10** (model card) documents `SELECTED_FEATURES` + the leakage/anchor audits + the `n_per_sector` report + the importance/stability table; **05-11** runs the live panel to populate the regime/anchor/DRHP-numeric values and regenerate `SELECTED_FEATURES` + the committed records.
- **FCAST-02 and FCAST-05 remain Pending** in REQUIREMENTS.md — do not close them until the render half + real-panel proof (05-11) and the committed model card (05-10) land. This plan delivered only the (offline-proven) four-family available_at feature-leakage expansion + lean selection + the D5-09 support helper.
- Carry-overs that do NOT block Phase 5 code: (1) the 03-05 live `make release` numeric-gate (human-only); (2) the real historical-panel build + live regime/anchor fetch is the 05-11 checkpoint (the 05-01 synthetic fixtures + tmp-dir caches unblock every test until then).

## Self-Check: PASSED

- Created files verified on disk: `pipelines/features/select.py`, `tests/unit/test_features_expanded.py`, `tests/unit/test_feature_selection.py` — all FOUND; modified files (`sources.py`, `features/__init__.py`, `features/build.py`, `test_features_available_at.py`) FOUND.
- Task commits verified in git log: `b4848e9` FOUND, `944c698` FOUND, `90c5801` FOUND.
- Plan verification re-run: `pytest tests/unit/test_features_available_at.py tests/unit/test_features_expanded.py tests/unit/test_feature_selection.py -q` → 24 passed; Task 1 inline check (regime specs present, no gmp/subscri column) exits 0; `test_forecast_isolation.py` → 11 passed; full `pytest tests/unit -q` → 455 passed / 0 skipped / 1 pre-existing ignorable embedder failure (442 → 455 = +13 new tests, no regression).

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-19*
</content>
</invoke>
