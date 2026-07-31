---
phase: 05-calibrated-listing-day-forecaster
plan: 09
subsystem: forecasting
tags: [baselines, diebold-mariano, wilcoxon, release-gate, conformal, abstention, walk-forward, honesty]

# Dependency graph
requires:
  - phase: 05-05
    provides: walk_forward as-of-T0 loop + r2_leakage_alarm (the R²>0.5 gate this consumes)
  - phase: 05-06
    provides: OOS_COLUMNS walk-forward frame contract + precompute consumer of walk_forward
  - phase: 05-08
    provides: training_support / is_out_of_support (D5-09 out_of_support input) + pool_sectors (D5-10)
provides:
  - "pipelines/forecast/baselines.py: baselines_asof (four as-of-T0 baselines) + score_baselines + inline dm_test (Harvey-corrected) + wilcoxon_robustness + release_gate (P9 verdict)"
  - "pipelines/forecast/walkforward.py: D5-09 opt-in abstention (out_of_support + interval_too_wide) completing all three ForecastRecord reasons"
  - "The P9 release gate: FAIL on R²>0.5 leakage OR baseline-beats-model; honest PASS-with-note on a tie"
affects: [05-10 model card (embeds DM table + verdict), 05-11 live build (enables the tuned abstention guards + real gate run)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline ~15-line Diebold–Mariano (Harvey 1997 small-sample correction, scipy.stats.t) — NO third-party DM dependency (attack-surface reduction, T-05-09-SC)"
    - "Plain-data release verdict (dict of per_baseline DM stats + notes, no plotting) so the model card embeds it verbatim"
    - "Opt-in D5-09 abstention guards default OFF (untuned until the live panel, Open Q3) so the default walk_forward call is behaviourally unchanged"
    - "Lazy in-function import of pipelines.features.select inside walk_forward to break the select<->walkforward import cycle and keep the module import offline"

key-files:
  created:
    - pipelines/forecast/baselines.py
    - tests/unit/test_baselines_dm.py
    - tests/unit/test_release_gate.py
    - tests/unit/test_walkforward_abstention.py
  modified:
    - pipelines/forecast/walkforward.py

key-decisions:
  - "The four baselines are scored under the IDENTICAL as-of-T0 pool (listing_date < T0_i) as the model; sector_mean uses the D5-10 'Other'-pooled sector — the model is never given an easier evaluation than the baselines (P9)"
  - "DM stays inline with the Harvey small-sample correction; the low-download [ASSUMED] third-party DM PyPI package is deliberately avoided (T-05-09-SC)"
  - "The P9 gate FAILS on R²>0.5 leakage OR a baseline significantly beating the model (DM p<0.05 in its favour), and PASSES honestly on a statistical tie with an explicit 'does not significantly outperform' note (D5-01; no p-hacking)"
  - "The two D5-09 abstention guards are OPT-IN (check_support / max_width / width_iqr_mult all default disabled) — their thresholds are untuned until 05-11 (Open Q3), so firing them on synthetic data would be arbitrary AND would break the existing no-lookahead fixture; production enables them at 05-11"
  - "FCAST-05 / FCAST-03 left Pending — the baselines/DM/gate half is built and offline-green, but the model card render (05-10) and real-panel proof (05-11) are still open (mirrors 05-05/05-06/05-08 honest-Pending posture)"

patterns-established:
  - "Honesty gate as plain-data: release_gate returns {passed, r2, r2_alarm, per_baseline{...}, notes} the model card embeds — no display coupling"
  - "Isolation source audit gotcha: a module's own docstring must avoid the literal forbidden tokens ('xgboost'/'mapie'/'shap'/DM-package) so the inspect.getsource substring audit stays green (same class as the 'shape'->'shap' gotcha)"

requirements-completed: []  # FCAST-05 / FCAST-03 remain Pending (model card 05-10 + real-panel proof 05-11)

# Metrics
duration: 35min
completed: 2026-07-19
---

# Phase 5 Plan 09: Baselines + Diebold–Mariano P9 Release Gate + D5-09 Abstention Summary

**Four as-of-T0 baselines + an inline Harvey-corrected Diebold–Mariano test compose the honest P9 release gate (FAIL on R²>0.5 leakage or baseline-beats-model, PASS-with-note on a tie), and the walk-forward gains the two opt-in D5-09 abstention halves (out_of_support + interval_too_wide) that complete all three ForecastRecord reasons.**

## Performance

- **Duration:** ~35 min (resume of an interrupted run)
- **Completed:** 2026-07-19
- **Tasks:** 3
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments
- Verified + committed the interrupted executor's Task 1 work (baselines + inline DM + Wilcoxon) after fixing a genuine isolation-audit defect (docstring named the forbidden tokens).
- Confirmed the ahead-of-schedule `release_gate` was complete and correct by writing + running its full test (fail-on-leakage, fail-on-baseline-beat, honest-tie-pass).
- Wired the D5-09 conformal-native abstention (out_of_support + interval_too_wide) into `walk_forward` as opt-in guards, keeping the existing no-lookahead fixture behaviourally unchanged.
- Full suite: **474 passed / 0 skipped / 1 pre-existing embedder failure** (sentence-transformers not installed — unrelated; +19 new tests over the 455 baseline, no regression).

## Task Commits

Each task was committed atomically:

1. **Task 1: Four baselines as-of-T0 + inline Diebold–Mariano + Wilcoxon** - `7d78b6b` (feat)
2. **Task 2: P9 release gate (DM vs 4 baselines + R²>0.5 leakage alarm)** - `783ecfe` (feat)
3. **Task 3: D5-09 conformal abstention (out_of_support + interval_too_wide) in walk_forward** - `0a722c0` (feat)

**Plan metadata:** committed separately (this SUMMARY + STATE + ROADMAP).

## Files Created/Modified
- `pipelines/forecast/baselines.py` (created) - `baselines_asof` (predict_zero / global_median / trailing_12 / sector_mean, all from the as-of-T0 pool), `_pool_sector_labels` (local D5-10 'Other'-pooling), `score_baselines` (rebuilds each covered OOS row's as-of-T0 pool + aligns baseline abs-errors to the model's), inline `dm_test` (MAE-loss differential, Harvey 1997 correction, scipy.stats.t), `wilcoxon_robustness` (A7 paired signed-rank cross-check), `release_gate` (the P9 plain-data verdict). Model-free (numpy/pandas/scipy only), no network, no GMP/display reference.
- `pipelines/forecast/walkforward.py` (modified) - `walk_forward` gains three opt-in kwargs (`check_support`, `max_width`, `width_iqr_mult`) + two abstention branches: `out_of_support` (before fitting, via `is_out_of_support` on the proper-train support) and `interval_too_wide` (after `predict_band`, via `_width_guard` = tighter of the absolute + IQR-relative guards). `select` imported lazily to break the cycle.
- `tests/unit/test_baselines_dm.py` (created) - 10 tests: four exact baselines, empty-pool NaN honesty, DM significant/tie/degenerate/too-few, Wilcoxon, as-of-T0 pool strictness, D5-10 pooled sector_mean, model-free + lazy-import isolation.
- `tests/unit/test_release_gate.py` (created) - 4 tests: fail-on-leakage (R²>0.5), fail-on-baseline-beat, honest-tie-pass-with-note, plain-data verdict shape.
- `tests/unit/test_walkforward_abstention.py` (created) - 5 tests: out_of_support (checked), opt-in-default-covers, interval_too_wide (absolute + IQR-relative), in-support-tight-is-scored.

## Decisions Made
- **Baselines scored as-of-T0, identical to the model (P9).** Every baseline is computed only from `pool = rows[listing_date < T0_i]`; `sector_mean` uses the D5-10 'Other'-pooled sector. Baselines never see data the model didn't.
- **Inline Harvey-corrected DM, no dependency.** `dm<0 & p<0.05` = the model's loss is significantly lower; a degenerate zero-variance differential returns `(0.0, 1.0)`; fewer than two paired points returns `(NaN, NaN)`. Wilcoxon added as the distribution-free A7 robustness cross-check.
- **The gate tells the truth, not flatters the model.** FAIL on R²>0.5 leakage OR any baseline significantly beating the model; PASS on a tie with an explicit humility note (a pre-apply, no-demand model is expected to be humble, D5-01). No p-hacking.
- **D5-09 guards opt-in, defaults off.** Thresholds are untuned until the live panel (Open Q3). Turning them on with arbitrary synthetic thresholds would both be dishonest and break the existing no-lookahead fixture (a probe showed 6/36 covered folds would flip to out_of_support and the max band width is ~4× the min training IQR). The production precompute enables them at 05-11.
- **FCAST-05 / FCAST-03 stay Pending.** The baselines/DM/gate + abstention are built and offline-green, but the model-card render is 05-10 and the real-panel gate run is 05-11 — closing the requirements now would be dishonest (mirrors the phase's consistent honest-Pending posture).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Isolation-audit defect: baselines.py docstring named the forbidden tokens**
- **Found during:** Task 1 (verifying the uncommitted work)
- **Issue:** `test_baselines_is_model_free_and_display_isolated` does an `inspect.getsource` substring audit forbidding `xgboost`/`mapie`/`shap`/the DM package name. The interrupted executor's `baselines.py` module docstring literally wrote "MODEL-FREE (no xgboost / mapie / shap)" and named the DM package twice — so the module failed its own isolation test (same class as the project's known `'shape'->'shap'` gotcha).
- **Fix:** Reworded the three docstring occurrences to describe the avoided libraries without the literal tokens ("gradient-boosting / conformal / explainability library"; "third-party DM package").
- **Files modified:** pipelines/forecast/baselines.py
- **Verification:** `test_baselines_dm.py` 10/10 pass.
- **Committed in:** `7d78b6b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug). The `release_gate` was found already complete and correct (no fix needed) — the prompt's "may be incomplete" hedge did not materialise; I verified it by writing + running the full gate test rather than rewriting working code.
**Impact on plan:** The auto-fix was necessary for the isolation invariant. No scope creep.

## Issues Encountered
- **Atomic-commit split of a single new file.** `baselines.py` arrived from the interrupted run already containing `release_gate` (Task 2 code). To keep commits atomic per the plan's Task 1/Task 2 boundary, I backed up the full file, produced a Task-1 version without `release_gate` (via a deterministic transform, byte-safe), committed Task 1, then restored the exact original bytes for Task 2 — the Task 2 diff is 111 pure insertions, zero modifications to Task 1 code.
- **Circular import.** `pipelines.features.select` imports walk-forward constants at module level, so importing `select` at the top of `walkforward.py` would cycle. Resolved with a lazy in-function import inside `walk_forward` (consistent with the module's existing lazy-import posture; the module-load-is-offline test stays green).
- **Covered-row abstain_reason representation.** pandas coerces the covered rows' `abstain_reason=None` to `NaN` at DataFrame construction; the abstention test asserts `pd.isna(...)` for covered rows (pre-existing representation behaviour, unchanged by this plan).

## User Setup Required
None - no external service configuration required. The D5-09 guard thresholds and the real gate run are enabled/executed on the live panel at 05-11.

## Next Phase Readiness
- **05-10 (model card):** `release_gate` returns a plain-data verdict (`per_baseline` DM stats + Wilcoxon + `notes` + `r2`/`r2_alarm`) ready to embed as the DM table + P9 verdict; the A7 cross-sectional-DM caveat is documented for the card.
- **05-11 (live build):** enable `check_support=True` + tune `max_width`/`width_iqr_mult` from the real training-return IQR; run `release_gate` on the real ~200–300-row panel — if the model genuinely loses to a baseline there, the gate FAILING is the correct honest result (do not tune to force a pass).
- **Honesty invariants intact:** baselines.py + walkforward.py import no GMP/display signal; no `dieboldmariano` dependency; the R²>0.5 alarm is consumed as a hard gate.

## Self-Check: PASSED

All created/modified files exist on disk; all three task commits (`7d78b6b`, `783ecfe`, `0a722c0`) exist in history. Plan tests: 19/19 pass; full suite 474 passed / 1 pre-existing embedder failure (no regression).

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-19*
