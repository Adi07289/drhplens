---
phase: "05"
status: passed
verified: 2026-07-27
method: goal-backward (against ROADMAP Phase 5 success criteria) + live-app evidence
---

# Phase 5 Verification — Calibrated Listing-Day Forecaster

**Verdict: ACHIEVED (5/5 success criteria).** The P9 release gate HONESTLY FAILS
(naive baselines beat the model) — this is the EXPECTED D5-01 result for a pre-apply,
no-demand forecast and a PASS condition for the phase goal (build an honestly
backtested forecaster with a truthful model card), not a failure.

| SC | Requirement | Verdict | Evidence |
|----|-------------|---------|----------|
| 1 | 80% interval as the dominant visual, no green/red, no point headline (FCAST-01, UI-03) | ✅ | ui/forecast_block.py `_plot_html` (band width = message, P21); verified live on /snapshot |
| 2 | GMP-vs-model gap called out explicitly (GMP-03) | ✅ | `_gap_html` + FORECAST_GMP_GAP_TEMPLATE; test_gmp_implied_conversion ("implies X% above/below the GMP-free median") |
| 3 | Empirical coverage / MAE / per-year RMSE surfaced to any user (FCAST-04) | ✅ | `_tested_strip_html`; verified live on /snapshot (80.0% / MAE 0.4 / 2003-2026 / n=1132), reconciled to the live run |
| 4 | Committed model card: window, features+available_at, 4 baselines+DM, calibration/PIT/SHAP, limitations (FCAST-03, FCAST-05) | ✅ | model_card/MODEL_CARD.md; verified live on /methodology; real SHAP regenerated this session |
| 5 | Every feature available_at≤T0; GMP+subscription excluded; leakage audit documented (FCAST-02) | ✅ | build_features LeakageError gate + EXCLUDED_FROM_MODEL + anchor_leakage_audit; test_forecast_isolation green |

**Honest posture confirmed:** the model card + the /snapshot block lead with the
P9-FAIL verdict ("does not beat a naive baseline … calibration transparency, not a
validated call"); real SHAP shows the live panel is effectively one-feature
(trailing_listing_gain), disclosed via the "Populated live?" column + a one-feature
limitation. Nothing was p-hacked to cross the gate.

**Live evidence captured this session:** /methodology (P9 FAIL matching
release_gate.json, real SHAP, no seed banner), /snapshot (honest banner + live metrics
strip). Full unit suite: 530 passed, 0 failed.
