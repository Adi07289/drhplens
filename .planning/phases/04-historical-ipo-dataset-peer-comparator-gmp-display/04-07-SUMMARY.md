---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 07
subsystem: data
tags: [historical, survivorship, panel, live-build, fcast-03, chittorgarh, nse, jugaad-data, reproducibility]

requires:
  - phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
    provides: pipelines/historical/{sources,build,validate}.py + schema + tests (04-07 Tasks 1-2, offline)
provides:
  - the REAL survivorship-corrected historical IPO panel (data/historical/ipo_panel.parquet + .csv), 1378 rows
  - non-zero withdrawn count (P3 survivorship satisfied) + replace-with-NaN returns retained
  - validated ~7% median MAAR sanity result (10.19%, no divergence flag) — Phase 5 FCAST-03 foundation
affects: [05-11]

tech-stack:
  added: []
  patterns: [live issuer-side crawl (chittorgarh withdrawn index + NSE past-issues), jugaad-data/yfinance listing-day price, requests-cache + tenacity + per-item isolation]

key-files:
  modified:
    - data/historical/ipo_panel.parquet (real 1378-row survivorship-corrected panel — the canonical live build)
    - data/historical/ipo_panel.csv (git-diff mirror)
    - data/historical/README.md (median sanity result recorded)
  created:
    - .planning/phases/04-historical-ipo-dataset-peer-comparator-gmp-display/04-07-SUMMARY.md
---

# Phase 04 Plan 07 — Historical IPO Panel: LIVE full build (Task 3) Summary

**The deferred live/network checkpoint (Task 3) is closed: the committed `data/historical/ipo_panel.parquet` is the real 1378-row survivorship-corrected Indian mainboard IPO panel (non-zero withdrawn, replace-with-NaN returns retained, ~10.19% median within the ~7% MAAR sanity band, no divergence flag) — the honest FCAST-03 foundation Phase 5 backtests on — and the live crawler was re-run on 2026-08-15 to confirm it still reproduces end-to-end against live sources.**

## What ran / what is committed

- Tasks 1 & 2 (schema, `validate.py`, `build.py`, `sources.py`, `tests/unit/test_historical_panel.py`, offline SAMPLE) were already committed offline.
- The real panel was first produced at the 05-11 live build (2026-07-25) — the crawl of the chittorgarh withdrawn-IPO index + NSE public past-issues, with jugaad-data / yfinance for listing-day prices — and committed as the canonical `ipo_panel.parquet`. **This plan's SUMMARY formally closes Task 3 for that committed artifact.**

## Committed panel — real numbers (per Task 3 resume-signal)

| Metric | Value |
|--------|-------|
| Total rows | **1378** |
| Status distribution | `listed_alive` 1373 · **`withdrawn` 5** |
| Withdrawn/delisted count | **5** — non-zero (P3 survivorship assert passes) |
| Non-NaN listing-day returns | 1245 / 1378 (133 NaN **retained**, not dropped) |
| **Median listing-day return** | **10.19%** |
| Divergence flag | **none** (10.19% within band; < the ~20% survivor-inflation threshold) |

- Offline suite: `tests/unit/test_historical_panel.py` — **19 passed** against the real panel.

## Reproducibility check (2026-08-15)

Re-ran `.venv/bin/python -m pipelines.historical.build build` (LIVE) on real egress to confirm the crawler still works: it produced **1394 rows** with the same status distribution shape and an **identical 10.19% median** — the ~16-row delta is simply newer listings since July. **The committed panel remains the canonical 1378-row build** because the frozen 05-11 walk-forward OOS frame (`data/forecasts/_gate/oos_real.parquet`) + P9 release-gate verdict + model card were all computed against it, and that OOS frame is not cleanly re-runnable (it was an ad-hoc supervised run). Keeping the panel matched to the frozen gate preserves artifact consistency over marginal freshness.

## Honest limitations (recorded, not hidden)

- **Only 2 of 5 status values populated live** — `withdrawn` (5) present but **0 `delisted` / `merged` / `name_changed`** captured. The taxonomy + NaN-survivorship controls are correct and the P3 non-zero-withdrawn gate passes, but the withdrawn count (5) is modest for a 2014–present universe; richer delisted/merged capture is a follow-up data-source task, not a schema defect.
- Median 10.19% sits above the Shah & Mehta ~7.19% MAAR baseline but well inside the sanity band — the divergence flag (fires > ~20%) correctly stays quiet. Surfaced as-is on `/methodology`.

## Downstream

- This real panel is the input `05-11` consumed for the live walk-forward. That gate honestly **FAILED** (the model does not beat the naive baselines — D5-01), so no per-IPO forecast band was regenerated; see `05-11-SUMMARY.md`.
