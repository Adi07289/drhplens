# 05-11 — Live Build Runbook (deferred supervised crawl)

**Status:** 05-11 is PARTIALLY complete. This is NOT a plan SUMMARY — 05-11 stays `[ ]`
in ROADMAP until the real artifacts are committed and a human verifies `/methodology`.

| Task | State |
|---|---|
| **1 — verify + install `nse`** | ✅ **DONE.** Verified at the blocking-human legitimacy checkpoint (Sigstore attestation + PyPI Trusted Publishing + GPL-3.0 + 50 releases, github.com/BennyThadikaran/NseIndiaApi). Installed `nse 3.1.2` (+ `mthrottle`), declared in `pyproject.toml` (commit `84a5a9d`). |
| **2 — live universe build + real records + real model card** | ⏳ **CODE LIVE-READY, crawl deferred.** The build was genuinely unwired (see below); fixed + committed (`e7737c8`). The real ~1,400-IPO crawl + walk-forward + gate + artifact regeneration is the remaining supervised step. |
| **3 — human verify `/methodology` + honest P9 verdict** | ⬜ **PENDING** (depends on Task 2 producing real artifacts). |

## What was discovered at the live pull (and fixed)

Probing the live sources (egress confirmed: pypi/sebi/chittorgarh 200; nseindia 403 is
expected bot-detection) surfaced three defects the offline SAMPLE panel masked because it
hand-provides listing-day closes:

1. **`coerce_date` couldn't parse the live date shape.** Both sources use `DD-Mon-YYYY`
   (NSE `14-JUL-2026`, chittorgarh `19-Aug-2024`) — not in the format list, so NSE
   `issue_date` (= T0, the leakage-gate anchor) silently parsed to `None`. Added `%d-%b-%Y`.
2. **NSE parser used the wrong key.** Real key is `ipoStartDate` (code probed
   `issueStartDate`); also `symbol` was never kept. Fixed + threaded `symbol`.
3. **Source B (withdrawn overlay) HTML scraper is dead** (`soup.find("table")` → None — the
   04-07 JS-migration blocker), for BOTH SEBI and chittorgarh. Repointed
   `_fetch_chittorgarh_withdrawn` to the **webnodejs JSON API** (report 202),
   `data-read/202/1/50/{fyEnd}/{FY}/0/0`, iterating recent FYs + dedupe. SSRF-allow-listed
   `webnodejs.chittorgarh.com`.
4. **`build_panel` had an UNWIRED TARGET.** `fetch_listing_day_close()` was defined but
   never called; NSE past-issues carries no close, so `listing_day_return` (the target) was
   all-NaN → `walk_forward` would get **zero scorable rows**. Wired `_enrich_listing_closes`
   into `build_panel` (per-symbol jugaad-data → yfinance → None).

All four proven offline (+6 monkeypatched tests in `test_historical_panel.py`).

**Bounded live validation (evidence the fixes work):**
- Source A (NSE, 120-day window): 42 rows, all 42 with `issue_date` + `symbol` parsed, 38 listed.
  A 12-year query returns **~1,436 listed IPOs** — a real multi-year universe.
- Source B: 5 real withdrawn IPOs via the JSON API (Ecom Express, MEIR Commodities, Tea Post,
  Sai Infinium) → **non-zero withdrawn (P3 satisfied)**.

## Resume runbook — the supervised crawl (run in an env with egress)

```bash
# 1. Live universe build (Source A NSE listed core + Source B withdrawn overlay).
#    This ALSO runs the per-symbol listing-day-close enrichment (~1,400 calls,
#    jugaad-data → yfinance; SLOW + rate-limit-prone — supervise it).
.venv/bin/python -m pipelines.historical.build build
#    -> data/historical/ipo_panel.{parquet,csv}; confirm non-zero withdrawn/delisted
#       + a median near the ~7% MAAR band (else the divergence flag fires on /methodology).

# 2. Refresh the lean feature set on the real panel, run the walk-forward
#    (MLflow-tracked), score the four baselines, and PERSIST the gate inputs:
#    data/forecasts/_gate/oos_real.parquet + release_gate.json  (see 05-11-PLAN Task 2).

# 3. HARD-assert the gate BEFORE committing anything (05-11-PLAN Task 2 <verify>):
.venv/bin/python -c "
import pandas as pd
from pipelines.forecast.walkforward import r2_leakage_alarm
from pipelines.forecast.baselines import release_gate
panel = pd.read_parquet('data/historical/ipo_panel.parquet')
assert int(panel['status'].isin(['withdrawn','delisted']).sum()) > 0, 'P3: zero withdrawn'
oos = pd.read_parquet('data/forecasts/_gate/oos_real.parquet')
_, alarm = r2_leakage_alarm(oos); assert alarm is None, 'P4: R2>0.5 leakage — STOP'
assert release_gate(oos, panel)['passed'] is True, 'P9: gate FAILED — do not commit'
"

# 4. ONLY if the gate passes: regenerate + commit the REAL records + model card + mlruns.
.venv/bin/python -m pipelines.forecast.precompute precompute-all   # track=True
.venv/bin/python -m pipelines.forecast.card build   # regenerates model_card/ from real run
.venv/bin/python -m pytest tests -q   # full suite green against real artifacts

# 5. Human: open the app, verify the /methodology model card renders honestly and the
#    shown P9 verdict matches release_gate.json. Then mark 05-11 complete.
```

## Known limitations / caveats for the crawl

- **Withdrawn overlay is recent-coverage only.** Chittorgarh report 202 returns ~recent-FY
  withdrawals (2024–2025+); pre-2025 withdrawn coverage needs SEBI, whose HTML scraper is
  dead (`fetch_sebi_offer_documents` → 0 rows). Non-zero withdrawn is satisfied, but the
  survivorship overlay is thinner than the full 2014-present ideal — surface this honestly
  in the model card's limitations.
- **`issuePrice` format unconfirmed for listed rows.** The live probe only saw `"-"`
  (upcoming). If NSE returns `"Rs.240"`, `coerce_price` mis-scales (`"Rs.240"` → 0.24 via the
  `"Rs"`-strip leaving a leading `.`). Verify on the first listed pull; harden `coerce_price`
  if needed.
- **Enrichment is ~1,400 per-symbol calls** (jugaad-data bhavcopy + yfinance fallback) —
  slow and NSE-throttle-prone. Consider a bounded window first, and expect many NaN targets
  (retained, never fabricated).
- **`mlruns/` is currently gitignored** (`.gitignore` line ~45). The plan wants the real run
  committed — `git add -f mlruns/<run>` or un-ignore before committing.
- **`.cache/` and `data/historical/raw/`** (nse download dir, requests cache, raw source
  snapshots) are regenerable local artifacts — gitignore them before the crawl so they are
  not accidentally committed.
- **The P9 gate may honestly FAIL** on the real data (a pre-apply, no-demand model is
  expected to be humble, D5-01). If a baseline significantly beats the model, the gate
  FAILING and STOPPING the commit is the correct, honest outcome — an honest "does not
  significantly outperform" verdict is itself a legitimate, portfolio-worthy result. Do NOT
  p-hack features to force a pass.
