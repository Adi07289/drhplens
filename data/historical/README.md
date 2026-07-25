# Historical IPO Panel (survivorship-corrected)

**Artifact kind:** FULL LIVE BUILD
**Generated:** 2026-07-25
**Rows:** 1378

## Column contract

| Column | Meaning |
|---|---|
| `issuer` | Company name as disclosed |
| `issue_date` | DRHP/issue date |
| `listing_date` | Exchange listing date (NaT if never listed) |
| `issue_price` | Final IPO offer price per share (INR) |
| `listing_day_close` | Listing-day EOD close (INR; NaN if unavailable) |
| `listing_day_return` | (close − issue) / issue (NaN when unknown — the target) |
| `status` | One of ['delisted', 'listed_alive', 'merged', 'name_changed', 'withdrawn'] |

**Survivorship (P3):** the universe is sourced issuer-side (chittorgarh /
SEBI, which include withdrawn/pulled IPOs). A company with no listing-day
price is kept with `listing_day_return = NaN` (replace-with-NaN) — the
absence is COUNTED, never dropped.

## Median MAAR sanity-check

- **Median listing-day return (scored rows):** 10.19%
- **Divergence flag:** none (in-band)

Median listing-day return is sanity-checked against the ~7.19% MAAR baseline (Shah & Mehta 2015, 113 NSE mainboard IPOs 2010–2014). A built median outside [-5%, 20%] raises a plain-text divergence flag; a median above 20% is read as survivorship inflation (dropped withdrawn/delisted IPOs).

- **Status distribution:** listed_alive=1373, withdrawn=5
- **Parquet written:** True (else CSV is the source of truth; install `pyarrow` — runbook dependency)

## Runbook — full live build (deferred 04-07 checkpoint)

Run in an environment with internet egress (chittorgarh/SEBI/NSE):

```bash
.venv/bin/python -m pipelines.historical.build build
```

Then confirm: row count ~800–1000, withdrawn/delisted statuses present
(zero in a 2014-present universe is a survivorship red flag), and the
median near the ~7% MAAR band (else the divergence flag above fires and is
surfaced verbatim on /methodology). Commit the resulting parquet + CSV.
