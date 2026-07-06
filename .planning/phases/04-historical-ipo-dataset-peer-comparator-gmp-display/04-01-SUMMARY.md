---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 01
subsystem: infra
tags: [yfinance, jugaad-data, nse, requests-cache, integration-tests, ci]

requires: []
provides:
  - yfinance==1.5.1 + requests-cache==1.3.3 + jugaad-data==0.33.1 pinned & installed
  - validated yfinance .info peer-multiple key set (trailingPE/priceToBook/enterpriseToEbitda/returnOnEquity)
  - validated jugaad-data NSE endpoints (stock_df + bhavcopy) — WORKING as of 2026-07-06
  - two integration smoke tests + nightly-nse.yml drift-detection CI
affects: [04-03 peer_sources, 04-07 historical panel]

tech-stack:
  added: [yfinance==1.5.1, requests-cache==1.3.3, jugaad-data==0.33.1]
  patterns: [env-gated integration smoke (NSE_LIVE_SMOKE), nightly drift-detection CI]

key-files:
  created: [tests/integration/test_yfinance_nse_smoke.py, tests/integration/test_jugaad_data_nse.py, .github/workflows/nightly-nse.yml]
  modified: [pyproject.toml]

key-decisions:
  - "jugaad-data endpoints WORK (live-verified) — use as primary NSE source; no yfinance-only fallback needed"
  - "Integration smokes skip unless NSE_LIVE_SMOKE=1 so unit + full suites stay green offline"

patterns-established:
  - "Env-gated live integration smoke: pytest.mark.integration + skipif(NSE_LIVE_SMOKE != 1)"
  - "Nightly GitHub Actions drift detection for external data sources (schedule + workflow_dispatch)"

requirements-completed: [PEER-02]

duration: 25min
completed: 2026-07-06
---

# Phase 4 · Plan 01: NSE/Yahoo data-source spike Summary

**The Indian market-data sources are validated and pinned — yfinance 1.5.1 returns all four peer-multiple keys and jugaad-data's NSE endpoints are confirmed WORKING against live NSE, so the peer table (04-03) and historical panel (04-07) build on verified sources, not assumptions.**

## What shipped

- **Deps pinned + installed** (after the Task 1 human package-legitimacy gate — user approved): `yfinance==1.5.1`, `requests-cache==1.3.3`, `jugaad-data==0.33.1` in `pyproject.toml`, installed into `.venv`.
- **Two integration smoke tests** (`@pytest.mark.integration`, skip unless `NSE_LIVE_SMOKE=1`): `test_yfinance_nse_smoke.py` (RELIANCE.NS `.info` peer-multiple keys) and `test_jugaad_data_nse.py` (NSE `stock_df` candle + bhavcopy).
- **`.github/workflows/nightly-nse.yml`** — scheduled (01:30 UTC) + `workflow_dispatch` job running the live smokes so NSE drift is caught early, never gating unit CI.

## Live spike verdict (Task 3 — run 2026-07-06)

- **jugaad-data: WORKING.** `stock_df("RELIANCE", …, series="EQ")` returns candles; `bhavcopy_raw(2024-11-20)` returns content. **Verdict: use jugaad-data as the primary NSE source** for 04-07 — no fall-back-to-yfinance-price needed at this time. (One benign warning: np.datetime64 tz representation.)
- **yfinance .info key coverage for RELIANCE.NS** (all four populated, all `float`):

  | Key | Value | Peer multiple |
  |-----|-------|---------------|
  | `trailingPE` | 22.12 | P/E |
  | `priceToBook` | 1.98 | P/B |
  | `enterpriseToEbitda` | 12.17 | EV/EBITDA |
  | `returnOnEquity` | 0.0914 | ROE |

  **Note for 04-03:** `returnOnEquity` is a FRACTION (0.0914 = 9.14%) — multiply by 100 for percent display. `.info` carries 172 keys total.

## Verification

- `pytest tests/unit -q`: 314 passed (+ the pre-existing bge-m3 embedder failure, ignored) — no regression from the yfinance major bump.
- Whole suite: **328 passed, 10 skipped** (7 + the 3 new env-gated smokes), 7 xfailed. Integration smokes skip cleanly offline.
- Live spike: **3 passed** under `NSE_LIVE_SMOKE=1`.
- `yfinance.__version__ == "1.5.1"`; `requests_cache` + `jugaad_data` import cleanly.

## Notes

- Commit: `5f37c7c`.
- All three tasks complete (Task 1 human-approved, Task 2 auto, Task 3 live spike run — not deferred). This unblocks Wave 2 (04-03, 04-04, 04-07).

## Self-Check

- [x] `pyproject.toml` contains `jugaad-data`; yfinance pinned 1.5.1.
- [x] Both integration smoke files contain `pytest.mark.integration`; nightly workflow contains `schedule`.
- [x] Live spike verdict + yfinance key coverage recorded above.
- [x] Unit/full suites green offline (minus the ignored embedder test).
