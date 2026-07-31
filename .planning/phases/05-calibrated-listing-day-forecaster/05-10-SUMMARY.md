---
phase: 05-calibrated-listing-day-forecaster
plan: 10
subsystem: forecast
tags: [model-card, calibration-plot, pit-histogram, shap, diebold-mariano, release-gate, leakage-audit, methodology, render-isolation, matplotlib, code-now-defer, honesty, fcast-03, fcast-05, ui-03]

# Dependency graph
requires:
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-06 diagnostics.global_metrics (the raw-coverage seam the plots + card share) + the seed data/forecasts record metrics block; 05-07 the forecast block's 'Full model card →' link (whose destination this builds); 05-08 leakage_audit + anchor_leakage_audit (D5-08) + pool_sectors n-per-sector (D5-10) + SELECTED_FEATURES (D5-07); 05-09 release_gate (four baselines + Diebold–Mariano + P9 verdict) + r2_leakage_alarm; 05-05 walk_forward (the fold engine the seed DM runs over); pipelines.forecast.model make_quantile_models (the SHAP model)"
provides:
  - "pipelines/forecast/diagnostics.py: calibration_plot + pit_histogram + shap_summary -> committed PNGs (lazy matplotlib/shap, Agg headless) + empirical_coverage (the shared raw-coverage seam); global_metrics untouched"
  - "pipelines/forecast/card.py: build_model_card assembling model_card/MODEL_CARD.md (+ card_data.json) from computed inputs (metrics + release_gate DM + leakage/anchor audits + SELECTED_FEATURES + n-per-sector + limitations); default_seed_inputs (CODE-NOW-DEFER seed)"
  - "committed model_card/ artifacts: MODEL_CARD.md, card_data.json, calibration.png, pit.png, shap.png (seed / not-yet-regenerated)"
  - "pages/01_methodology.py: the render-only forecaster model-card section (UI-03 link destination) — plots + DM table + leakage/anchor audit + n-per-sector + limitations grid, imports no model module"
affects: [05-11 live build (regenerates the real card + PNGs + runs the P9 gate on the real panel)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy-plotting diagnostic builders: matplotlib/shap imported INSIDE each function + Agg headless backend forced, so importing diagnostics.py stays offline (pinned by a subprocess module-load audit); global_metrics (05-06) kept byte-identical"
    - "Grid-derived reliability/PIT from the committed band: a fine 0.05..0.95 quantile grid is derived from the 0.1/0.5/0.9 band via a Gaussian working σ (A8) PURELY for the plot; the calibration annotation uses the REAL held-out coverage (never 0.80-rounded, P17)"
    - "Computed-markdown model card (mirrors historical.build._write_readme): assemble MODEL_CARD.md from computed artifacts, never hand-narrated; an explicit SEED banner makes CODE-NOW-DEFER honest"
    - "Dual-output card writer: card.py emits MODEL_CARD.md (human) + card_data.json (plain data); the render-only page reads the JSON + PNGs so it imports no model/explainability module (T-05-10-ISO)"
    - "Import-pattern isolation audit (not bare-substring): the page legitimately references the committed shap.png artifact, so the render audit forbids model IMPORTS — the documented shape→shap filename gotcha"

key-files:
  created:
    - pipelines/forecast/card.py
    - model_card/MODEL_CARD.md
    - model_card/card_data.json
    - model_card/calibration.png
    - model_card/pit.png
    - model_card/shap.png
    - tests/unit/test_diagnostics_plots.py
    - tests/unit/test_model_card.py
    - tests/unit/test_methodology_render.py
  modified:
    - pipelines/forecast/diagnostics.py
    - pages/01_methodology.py

key-decisions:
  - "FCAST-03 / FCAST-05 / UI-03 left PENDING (requirements-completed empty) — the artifacts are committed but SEED (CODE-NOW-DEFER); the real card + PNGs + P9 gate regenerate from the live walk-forward at 05-11. Marking them complete on seed data would be dishonest (mirrors 05-06/07/08/09's consistent honest-Pending posture)."
  - "The calibration/PIT plots derive a 0.05..0.95 grid from the committed 0.1/0.5/0.9 band via a Gaussian working σ, fit PURELY for the diagnostic (A8); the production interval is unchanged and the plot is labelled grid-derived. The annotated 80% coverage is the REAL held-out global_metrics number (P17), never rounded to 0.80."
  - "The model card is assembled from COMPUTED inputs: seed forecast-record metrics (D5-12), a live walk_forward + release_gate DM table (P9), the static leakage_audit + anchor_leakage_audit (D5-08), SELECTED_FEATURES (D5-07), and pool_sectors n-per-sector over the real catalogue (D5-10). A prominent SEED / NOT-YET-REGENERATED banner states the provenance."
  - "card.py writes card_data.json alongside MODEL_CARD.md so the /methodology render reads plain data (+ PNGs) and imports NO xgboost/mapie/sklearn/shap/model module (T-05-10-ISO). The methodology render audit checks model IMPORT patterns rather than the bare 'shap' substring, because the page references the committed shap.png artifact (the shape→shap gotcha, documented in 05-09)."
  - "The seed P9 gate PASSES honestly (synthetic-fixture R²=-0.064 ≤ 0.5; no baseline significantly beats the model — the D5-01 'does not significantly outperform' humble case). Not tuned to force a pass; if the model genuinely loses on the real panel at 05-11 the gate FAILING is the correct result."
  - "The card is informational-only: _assert_clean forbids prescriptive advice tokens (buy/sell/subscribe/target/…) and obvious secrets/PII (T-05-10-HONEST / T-05-10-PII). The advice-token check uses the ADVICE verbs (not the technical stems) so the anchor exclusion stays describable without naming a banned stem."

patterns-established:
  - "empirical_coverage(oos_df) — the ONE raw-coverage seam the calibration annotation + the model card share (thin wrapper over global_metrics; never 0.80-rounded)"
  - "default_seed_inputs() — the CODE-NOW-DEFER seam that assembles the seed card from the current committed artifacts; the 05-11 live run swaps in the real oos_df-derived inputs with no card-writer change"

requirements-completed: []  # FCAST-03 / FCAST-05 / UI-03 remain Pending (seed artifacts; real regeneration + live P9 gate at 05-11)

# Metrics
duration: ~50min
completed: 2026-07-20
---

# Phase 5 Plan 10: Committed Model Card + /methodology Render Summary

**Built the phase's committed model card (Slice 3c, Success Criterion 4): three lazy-plotting matplotlib/SHAP diagnostic PNG builders (a reliability diagram annotated with the REAL held-out 80% coverage, a grid-derived PIT histogram, and a SHAP importance summary with a `feature_importances_` fallback — all Agg-headless, FCAST-03), a `build_model_card` writer that assembles `MODEL_CARD.md` ENTIRELY from computed inputs (training window + N, the lean `available_at ≤ T0` feature list, the anchor pre-open audit, the four baselines + Diebold–Mariano table with the P9 release-gate verdict, held-out coverage/MAE/per-year RMSE, the R²>0.5 alarm status, the n-per-sector report, and a plain Known-limitations section — FCAST-05), and the render-only `/methodology` forecaster model-card section that is the destination of the 05-07 forecast block's `Full model card →` link (UI-03) — all assembled from the CURRENT seed artifacts under an explicit SEED / NOT-YET-REGENERATED banner (CODE-NOW-DEFER; the real card + PNGs + live P9 gate regenerate at 05-11).**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-20
- **Tasks:** 3
- **Files modified:** 11 (9 created, 2 modified)
- **Tests:** `pytest tests/unit -q` → **496 passed / 0 skipped / 1 pre-existing embedder failure** (sentence-transformers absent — the documented ignorable failure, not a regression). +22 new tests over the 474 baseline (7 diagnostics-plots + 9 model-card + 6 methodology-render); the 05-03 forecast isolation audit (11 tests) stays green.

## Accomplishments
- **Task 1 — diagnostic PNG builders (FCAST-03).** Extended `pipelines/forecast/diagnostics.py` with `calibration_plot` (a reliability diagram of nominal-vs-empirical coverage across a 0.05..0.95 grid, ANNOTATED with the real held-out 80% coverage from `global_metrics`, never 0.80-rounded — P17), `pit_histogram` (the PIT/reliability histogram derived from the band-implied per-row σ, labelled grid-derived — A8), and `shap_summary` (mean `|SHAP value|` over the lean feature set via a `TreeExplainer`, falling back to `feature_importances_` when SHAP cannot explain the estimator). matplotlib/shap are imported LAZILY inside each function and the Agg headless backend is forced; `global_metrics` (05-06) is left byte-identical. `empirical_coverage` is the shared raw-coverage seam.
- **Task 2 — MODEL_CARD.md assembly (FCAST-05).** New `pipelines/forecast/card.py`: `build_model_card` mirrors `historical.build._write_readme`'s computed-markdown posture, stitching the training/backtest window + N, the lean `available_at ≤ T0` feature list (from `leakage_audit`), the explicit anchor pre-open audit (`anchor_leakage_audit`, D5-08), the four baselines + Diebold–Mariano table with the P9 `release_gate` verdict + Wilcoxon + the A7 cross-sectional caveat, the held-out coverage/MAE/per-year RMSE (P17), the R²>0.5 leakage-alarm status, the committed `calibration.png`/`pit.png`/`shap.png` refs, the `pool_sectors` n-per-sector report (D5-10), and a plain Known-limitations section (low R² is a feature, D5-01). `default_seed_inputs` assembles the seed from the current committed artifacts; the writer emits both `MODEL_CARD.md` and `card_data.json`; `_assert_clean` bars prescriptive advice tokens + secrets/PII.
- **Task 3 — /methodology render (UI-03).** Appended the "Forecaster · The listing-day model card" section to `pages/01_methodology.py`: it embeds the three committed PNGs via `st.image` (from `model_card/`), renders the four-baselines + DM `.drhp-metrics` table with the P9 verdict, the held-out coverage/MAE/R²-alarm line, the `available_at` leakage audit + the anchor pre-open audit (D5-08), the n-per-sector report (D5-10), and the Known-limitations `.drhp-hiw-card` grid — reading only `card_data.json` + the PNGs, HTML-escaping every card-derived string, and importing NO model/training/explainability module (T-05-10-ISO). It is the destination of the 05-07 forecast block's `Full model card →` link. The seed provenance is surfaced honestly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Calibration + PIT + SHAP diagnostic PNG builders (FCAST-03)** — `a027e37` (feat)
2. **Task 2: MODEL_CARD.md assembly from computed inputs (FCAST-05)** — `cdf0540` (feat)
3. **Task 3: /methodology forecaster model-card section render (UI-03)** — `b1f3a90` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

_Note: MVP mode ON / TDD mode OFF per the execution brief — each task's module + its tests were committed together in one atomic `feat` commit (no separate RED/GREEN commits), matching the 05-06/07/08/09 posture._

## Files Created/Modified
- `pipelines/forecast/diagnostics.py` (MODIFIED) — `QUANTILE_GRID`, `empirical_coverage`, `calibration_plot`, `pit_histogram`, `shap_summary` (+ `_scored_band`/`_band_sigma` helpers); lazy matplotlib/shap + Agg; `global_metrics` untouched.
- `pipelines/forecast/card.py` (NEW) — `CardInputs` dataclass, `build_model_card`, `default_seed_inputs`, `_render_markdown`/`_assert_clean`, seed assemblers (`_seed_metrics`/`_seed_release_verdict`/`_seed_n_per_sector`); `MODEL_CARD_DIR`/`PLOT_FILES`/`BANNED_ADVICE_TOKENS`.
- `model_card/MODEL_CARD.md` + `model_card/card_data.json` (NEW) — the committed seed public card + its plain-data twin.
- `model_card/calibration.png` + `pit.png` + `shap.png` (NEW) — the committed seed diagnostic artifacts.
- `pages/01_methodology.py` (MODIFIED) — the render-only forecaster model-card section + `_mc_num` helper + stdlib imports (`html`/`json`/`Path`).
- `tests/unit/test_diagnostics_plots.py` (NEW, 7) — non-empty PNG per builder, raw-coverage honesty, SHAP fallback, lazy-import subprocess audit, global_metrics-unchanged.
- `tests/unit/test_model_card.py` (NEW, 9) — markdown structure (plot refs / 4-row DM table + P9 verdict / available_at + anchor audit / R²-alarm + n-per-sector + limitations), no-banned-token, no-secret/PII, dual-file writer, seed-integration.
- `tests/unit/test_methodology_render.py` (NEW, 6) — plot embeds + DM table + leakage/anchor audit + n-per-sector + limitations grid + import-pattern isolation + committed-artifacts-exist.

## Decisions Made
- **FCAST-03 / FCAST-05 / UI-03 left Pending** — the artifacts are committed but SEED; the real regeneration + live P9 gate are 05-11. See key-decisions.
- **Grid-derived calibration/PIT from the committed band via a Gaussian working σ** (A8), annotated with the REAL held-out coverage (P17). See key-decisions.
- **Computed-markdown model card + a dual `card_data.json` output** so the render stays model-free (T-05-10-ISO). See key-decisions.
- **The seed P9 gate PASSES honestly** (humble R²; no baseline significantly beats the model — D5-01), not p-hacked.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical / isolation] Added `card_data.json` as the render's plain-data source**
- **Found during:** Task 3 (wiring the render)
- **Issue:** The plan directs the `/methodology` render to read "the committed `MODEL_CARD.md` / plain-data artifacts only" and import no model module. Parsing the DM table / audits back out of markdown at render time would be brittle, and importing `card.py` (which reaches `release_gate` → `walk_forward` → the model) would violate the T-05-10-ISO isolation invariant.
- **Fix:** `build_model_card(write=True)` now also emits `model_card/card_data.json` — the SAME assembled content as plain data. The page reads that JSON (+ the PNGs) with `json.load`, so it builds its tables without importing any model/explainability module. Pinned by `test_methodology_render.py`'s import-pattern audit.
- **Files modified:** `pipelines/forecast/card.py`, `pages/01_methodology.py`
- **Verification:** `test_methodology_render.py` (6/6) + `test_forecast_isolation.py` (11/11) pass.
- **Committed in:** `cdf0540` (Task 2, the writer) + `b1f3a90` (Task 3, the render)

---

**Total deviations:** 1 auto-fixed (Rule 2 — required to keep the render model-free while faithfully surfacing the computed card). **Impact on plan:** none to scope; it strengthens the T-05-10-ISO isolation invariant. No new dependencies; the module surface matches the plan's `must_haves.artifacts` and `key_links`.

## Known Stubs
- **All `model_card/` artifacts are SEED (CODE-NOW-DEFER), not the live backtest** — a phase-level decision, stated explicitly by the card's own SEED / NOT-YET-REGENERATED banner and by the render's seed caption. The calibration/PIT PNGs are drawn from a synthetic OOS frame and the DM table from a synthetic-fixture `walk_forward`; the held-out coverage/MAE/per-year RMSE come from the 05-01 seed forecast record. The REAL card + PNGs + P9 gate regenerate from the live survivorship panel at **05-11**. This is not a hidden stub — it is disclosed on the artifact and in the render.

## Issues Encountered
- **`shap.png` filename vs the `shap` isolation token.** The render must reference the committed `shap.png` artifact yet import no explainability library — the same `shape`→`shap` collision 05-09 documented. Resolved by making `test_methodology_render.py`'s isolation audit check model IMPORT patterns (`import shap`, `from shap`, the model dotted-paths) rather than the bare `shap` substring; the positive check still confirms all three PNG references.
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` still fails (`sentence-transformers is not installed`) — the documented ignorable embedder failure, unchanged by this plan. Suite: 474 → 496 passed (+22 new), same single embedder failure throughout.

## User Setup Required
None — no external service configuration required. The diagnostic builders + the card writer are offline code (matplotlib 3.11 / shap 0.51 already installed; Agg headless). The committed seed artifacts render `/methodology` offline today. The on-device 375px visual verification of the rendered section + the real card/PNG regeneration are the **05-11** checkpoint (this offline executor cannot run Streamlit).

## Next Phase Readiness
- **05-11 (live build):** call `precompute_forecasts` over the real survivorship panel → feed the resulting oos_df + `global_metrics` + `release_gate` into `build_model_card` (the writer is unchanged; only `default_seed_inputs` is replaced by the real inputs) and regenerate `calibration.png`/`pit.png`/`shap.png` from the real walk-forward + the fitted median model. Run the P9 gate on the real panel — if the model genuinely loses to a baseline there, the gate FAILING is the correct honest result (do NOT tune to force a pass). Then flip FCAST-03 / FCAST-05 / UI-03 to Complete and run the on-device human-verify checkpoint.
- **Isolation intact:** `pages/01_methodology.py` imports no model module (T-05-10-ISO, pinned); `diagnostics.py`/`card.py` are not scanned by the predictor↔display audit and reference no display/GMP signal.

## Self-Check: PASSED

- Created files verified on disk: `pipelines/forecast/card.py`, `model_card/{MODEL_CARD.md,card_data.json,calibration.png,pit.png,shap.png}`, `tests/unit/{test_diagnostics_plots,test_model_card,test_methodology_render}.py` — all FOUND; modified `pipelines/forecast/diagnostics.py` + `pages/01_methodology.py` FOUND.
- Task commits verified in git log: `a027e37` FOUND, `cdf0540` FOUND, `b1f3a90` FOUND.
- Plan verification re-run: `pytest tests/unit/test_diagnostics_plots.py tests/unit/test_model_card.py tests/unit/test_methodology_render.py tests/unit/test_forecast_isolation.py -q` → 33 passed; full `pytest tests/unit -q` → 496 passed / 0 skipped / 1 pre-existing ignorable embedder failure (no regression).

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-20*
</content>
