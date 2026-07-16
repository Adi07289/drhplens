---
phase: 5
slug: calibrated-listing-day-forecaster
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-15
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `05-RESEARCH.md` §"Validation Architecture". The historical-universe
> network step is a hard blocker, so validation must be derivable offline
> (monkeypatched fetchers), matching the proven Phase 2/3/4 posture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (`[tool.pytest.ini_options]`, `timeout=60`, strict markers) |
| **Config file** | `pyproject.toml` (+ existing `tests/conftest.py`, `tests/unit/conftest.py`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/unit -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests -q` |
| **Live/offline gate (existing)** | `make gate-test` (offline eval-gate fixture) |
| **Markers available** | `slow`, `eval` (`--run-eval`), `integration` (nightly live NSE test) |
| **Estimated runtime** | ~60 seconds (unit); integration excluded from quick loop |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/unit -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests -q`
- **Before `/gsd-verify-work`:** Full suite green + offline gate + (checkpoint) one live
  universe build with non-zero withdrawn/delisted rows.
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| FCAST-02 | every feature `available_at <= T0` | unit | `pytest tests/unit/test_features_available_at.py -x` | ❌ W0 | ⬜ pending |
| FCAST-02 / P4 | walk-forward train set ⊂ `{listing_date < T0_i}`; R²>0.5 alarm fires | unit | `pytest tests/unit/test_walkforward_no_lookahead.py -x` | ❌ W0 | ⬜ pending |
| FCAST-01 / FCAST-03 | CQR produces adaptive-width 80% interval on a fixture panel (offline, tiny) | unit | `pytest tests/unit/test_cqr_interval.py -x` | ❌ W0 | ⬜ pending |
| FCAST-04 | global coverage / MAE / per-year-RMSE computed correctly from OOS rows | unit | `pytest tests/unit/test_forecast_metrics.py -x` | ❌ W0 | ⬜ pending |
| FCAST-05 / P9 | 4 baselines scored as-of-T0; DM test + release-gate logic | unit | `pytest tests/unit/test_baselines_dm.py -x` | ❌ W0 | ⬜ pending |
| GMP-03 / FCAST-02 | render imports no model module; predictor imports no GMP | unit (isolation) | `pytest tests/unit/test_forecast_isolation.py -x` | ❌ W0 (mirror `test_gmp_isolation.py`) | ⬜ pending |
| FCAST-01 | forecast record round-trip + abstain / missing states | unit | `pytest tests/unit/test_forecast_schema.py -x` | ❌ W0 | ⬜ pending |
| FCAST-03 | survivorship: built panel has non-zero withdrawn/delisted; MAAR ~7% in band | unit (offline sample) + integration (nightly live) | `pytest tests/unit/test_historical_panel.py`; `pytest -m integration` | ⚠️ partial (extend existing) | ⬜ pending |
| UI-03 | forecast block renders band from a fixture record; empty / abstain / error states | unit (render) | `pytest tests/unit/test_forecast_block_render.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_features_available_at.py` — FCAST-02 leakage gate
- [ ] `tests/unit/test_walkforward_no_lookahead.py` — P4 (train ⊂ pre-T0; R²>0.5 alarm)
- [ ] `tests/unit/test_cqr_interval.py` — FCAST-01/03 (adaptive-width interval on a fixture)
- [ ] `tests/unit/test_forecast_metrics.py` — FCAST-04 (coverage / MAE / per-year RMSE)
- [ ] `tests/unit/test_baselines_dm.py` — P9 (baselines as-of-T0 + DM gate)
- [ ] `tests/unit/test_forecast_isolation.py` — mirror `test_gmp_isolation.py` (reverse audit)
- [ ] `tests/unit/test_forecast_schema.py` — record round-trip + abstain / missing states
- [ ] `tests/unit/test_forecast_block_render.py` — UI states from a fixture record
- [ ] Extend `tests/unit/test_historical_panel.py` — assert withdrawn/delisted present after two-source merge (monkeypatched fetchers)
- [ ] Add an `@pytest.mark.integration` nightly test hitting live NSE `public-past-issues` (CLAUDE.md requirement)
- [ ] Framework install: add xgboost / mapie / scikit-learn / mlflow / matplotlib / shap to `pyproject.toml`; `uv pip install` into `.venv`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| One live universe build produces non-zero withdrawn/delisted rows | FCAST-03 / P3 | Depends on live NSE/SEBI/chittorgarh availability + bot-detection; cannot be a deterministic CI unit | Run the universe-build CLI against live sources; assert `status ∈ {withdrawn, delisted}` count > 0 in the built panel before `/gsd-verify-work` |
| Calibration plot + PIT-style quantile diagnostic visually sane in model card | FCAST-03 / P17 | Visual artifact rendered into `/methodology`; empirical coverage is unit-tested but plot legibility is human-judged | Open `/methodology`, confirm calibration curve + PIT/quantile diagnostic + limitations render |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-16 (plan-checker confirmed all 11 plans satisfy Nyquist structural checks)
