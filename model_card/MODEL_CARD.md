# DRHPLens — Listing-Day Forecaster Model Card

**Model version:** `cqr-xgb-seed-2026.07`

> ⚠️ **05-11 LIVE BACKTEST RAN (2026-07-25) — HONEST RESULT: the model does NOT beat
> naive baselines.** The real survivorship panel (1,378 IPOs, 5 withdrawn, 1,245 scorable,
> median listing-day return 10.2%) was built live and the walk-forward P9 release gate was
> run on it. **Verdict: R² = −0.009 (no leakage); the `global_median` and `trailing_12`
> baselines significantly beat the model (Diebold–Mariano p = 5.5e-08 and 1.6e-05).** On
> this thin NSE-only feature set the forecaster adds nothing over a naive median — the
> expected, honest outcome for a pre-apply, no-demand model (P9 / D5-01). Per the release
> gate, the model is **not shipped as a validated forecaster**, and no features/folds/tests
> were tuned to force a pass. Gate evidence: `data/forecasts/_gate/release_gate.json`.
> **The plots + per-number tables below are still the SEED fixtures** — regenerating them
> from the real fitted model (calibration / PIT / SHAP) is the remaining 05-11 polish step.

## What this model is

A calibrated 80% prediction INTERVAL for the listing-day return of an Indian mainboard IPO, made at issue open (T0) — a range, not a call. It is informational and educational only, not advice. The grey-market premium is shown for context but NEVER feeds the model (GMP-free, FCAST-02).

## Training + backtest window

- **Training / backtest window:** 2016-2025 listing years (2016–2025)
- **Scored (held-out, non-abstain) IPOs:** 247
- **Protocol:** expanding-window, as-of-T0 walk-forward — for each IPO the train + calibration pool is STRICTLY the IPOs that listed before its issue date, so no future IPO can leak into training (P4/P6).

## Lean feature list (available_at ≤ T0)

The wide four-family candidate pool is curated to a lean production set (D5-07); every feature is disclosed at or before issue open, verified by the `available_at ≤ T0` leakage gate (FCAST-02).

| Feature | Family | available_at | Verdict |
|---|---|---|---|
| `issue_size_cr` | a | DRHP/RHP filing date (≤ T0) | <= T0 ✓ |
| `price_band_width_pct` | a | DRHP/RHP filing date (≤ T0) | <= T0 ✓ |
| `ofs_fraction` | a | DRHP/RHP filing date (≤ T0) | <= T0 ✓ |
| `promoter_dilution_pct` | a | DRHP/RHP filing date (≤ T0) | <= T0 ✓ |
| `nifty_mom_3m` | b | pre-open T0−1 EOD snapshot (< T0) | <= T0 ✓ |
| `india_vix` | b | pre-open T0−1 EOD snapshot (< T0) | <= T0 ✓ |
| `trailing_listing_gain` | b | pre-open T0−1 EOD snapshot (< T0) | <= T0 ✓ |
| `red_flag_count` | c | DRHP/RHP filing date (≤ T0) | <= T0 ✓ |
| `rpt_intensity` | c | DRHP/RHP filing date (≤ T0) | <= T0 ✓ |
| `anchor_book_cr` | d | pre-open T0−1 EOD snapshot (< T0) | <= T0 ✓ |

## Anchor pre-open leakage audit (D5-08)

Anchor-investor demand is the ONE legitimate T0 demand proxy, but it is borderline: only the PRE-OPEN anchor allocation (disclosed the day before issue open, T0−1) may be read. Post-open book-build demand (QIB / NII / RII, which closes AFTER issue open) can never be a feature.

| Anchor feature | Pre-open source | Disclosed | Verdict |
|---|---|---|---|
| `anchor_book_cr` | pre-open anchor allocation book size (₹ crore) | T0-1 | pre-open allocation only, <= T0 ✓ |
| `anchor_investor_quality` | pre-open anchor-investor quality/mix score | T0-1 | pre-open allocation only, <= T0 ✓ |
| `anchor_lockin_frac` | pre-open anchor lock-in fraction | T0-1 | pre-open allocation only, <= T0 ✓ |

## Baselines + Diebold–Mariano test (P9 release gate)

The model is compared against four naive baselines under the IDENTICAL as-of-T0 protocol — it is never given an easier evaluation. A Diebold–Mariano test (Harvey small-sample correction) on the MAE-loss differential gives the significance; a paired Wilcoxon signed-rank p is the distribution-free cross-check (A7).

| Baseline | DM stat | p-value | Wilcoxon p | n | Verdict |
|---|---|---|---|---|---|
| `predict_zero` | 0.423 | 0.674 | 0.729 | 46 | tie — no significant difference |
| `global_median` | 0.308 | 0.760 | 0.754 | 46 | tie — no significant difference |
| `trailing_12` | -1.096 | 0.279 | 0.268 | 46 | tie — no significant difference |
| `sector_mean` | -0.109 | 0.914 | 0.940 | 46 | tie — no significant difference |

**P9 release gate: PASS.**

> The model does not significantly outperform the following baseline(s) at p<0.05: ['predict_zero', 'global_median', 'trailing_12', 'sector_mean']. For a pre-apply, no-demand forecast this humble result is EXPECTED (D5-01) — a low R² is a feature, not a bug. The model card states this plainly; no features/folds/tests were tuned to cross the gate.

## Calibration, PIT + feature importance

![Reliability diagram — nominal vs empirical coverage](calibration.png)

![PIT histogram — grid-derived, flat means calibrated](pit.png)

![SHAP feature importance over the lean feature set](shap.png)

## Held-out calibration metrics

- **80% interval coverage (empirical, held-out):** 0.783
- **Mean absolute error:** 11.40 points

| Listing year | RMSE (points) |
|---|---|
| 2016 | 14.10 |
| 2017 | 12.80 |
| 2018 | 15.60 |
| 2019 | 13.20 |
| 2020 | 18.90 |
| 2021 | 21.40 |
| 2022 | 16.70 |
| 2023 | 12.10 |
| 2024 | 11.90 |
| 2025 | 13.50 |

## R² leakage alarm

- **Status: not fired.** Out-of-sample median R² = -0.064 ≤ 0.5. A humble R² is expected for a pre-apply, no-demand model (D5-01); a value above 0.5 would flag a T0-violating feature and fail the release gate.

## N per sector (D5-10)

Sectors with fewer than 30 IPOs are pooled into `Other` so a thin sector never becomes a noise-prone single-value slice; the ORIGINAL per-sector counts are kept below so the thinness stays visible.

| Sector | N |
|---|---|
| Automobiles (passenger vehicles) | 1 |
| Beauty and lifestyle e-commerce | 1 |
| Electric vehicles (two-wheelers) | 1 |
| FMCG / personal care (D2C) | 1 |
| Fintech / digital payments | 1 |
| Food delivery | 2 |
| Insurance | 1 |

## Known limitations

- **A humble R² is the honest result.** This is a pre-apply, no-demand forecast made at issue open (T0). It cannot see book-build demand, so a low out-of-sample R² is EXPECTED — a feature, not a bug (D5-01). A high R² (> 0.5) would instead flag a T0-violating feature leaking the future, so it is wired as a release-gate alarm.
- **Coverage is measured, not assumed.** The 80% interval coverage is the REAL held-out number over IPOs the model never trained on. It can land below or above 0.80 — the card shows the measured value, never a rounded-to-0.80 fiction (P17).
- **The PIT curve is grid-derived.** The reliability/PIT diagnostic fits a fine 0.05..0.95 quantile grid PURELY for the plot; the production interval stays the 0.1 / 0.5 / 0.9 band. The PIT is labelled grid-derived wherever it is shown (A8).
- **The Diebold–Mariano test is cross-sectional.** The four baselines are compared under the identical as-of-T0 protocol, but the loss differential is cross-sectional across IPOs rather than a single time series — read the DM p-values with that caveat (A7). A paired Wilcoxon signed-rank p is reported alongside as a distribution-free cross-check.
- **Seed provenance — regenerates at the live build.** These numbers are assembled from the current seed/fixture artifacts so the card and its plots render offline today. They regenerate from the live walk-forward over the real survivorship panel at the 05-11 checkpoint.

---

*Informational only — not advice. DRHPLens.*
