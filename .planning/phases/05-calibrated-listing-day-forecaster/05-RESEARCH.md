# Phase 5: Calibrated Listing-Day Forecaster - Research

**Researched:** 2026-07-15
**Domain:** Conformal quantile regression (XGBoost + MAPIE) · walk-forward backtesting · survivorship-safe Indian-IPO universe assembly · cache-only Streamlit render
**Confidence:** MEDIUM (HIGH on the modeling API surface; MEDIUM on the data-source blocker — see §Environment Availability and §Validation Architecture)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D5-01 — Cutoff = T0 issue-open ("pre-apply").** Every feature `available_at <= T0` (issue-open day). ROADMAP SC-5 is canonical; FCAST-02's literal "T−1 of listing" wording is **superseded** — plan against T0 issue-open and note the reconciliation. A low R² is the honest result; R²>0.5 is a leakage red flag.
- **D5-02 — Target = raw listing-day return %** = `(listing_day_close − issue_price) / issue_price` (the panel's existing `listing_day_return` column). Market conditions enter as **features**, not by adjusting the target. MAAR (market-adjusted) target rejected.
- **D5-03 — Interval = CQR (Conformalized Quantile Regression), adaptive width.** XGBoost quantile regressors (`reg:quantileerror` at ~0.1/0.9) wrapped in MAPIE conformal calibration → the 80% interval **width varies per IPO**. Split-conformal constant-width rejected. 80% coverage target locked by ROADMAP.
- **D5-04 — Universe source pivots to official NSE/BSE + SEBI archive.** The chittorgarh HTML scraper is dead (`fetch_chittorgarh_index` → 0 rows; site is now a Next.js app). Seed from SEBI issue/withdrawal filings so withdrawn/pulled/delisted IPOs survive (P3). Exchange "listed" feeds skew survivor-only and must NOT be the sole source. chittorgarh JSON API (`webnodejs …/data-read/83/…`) is **optional enrichment/cross-check only**.
- **D5-05 — Verified subset first (~200–300 IPOs), full pipeline E2E, THEN expand N.** De-risks the data blocker; protects the ≥35% non-LLM modeling budget (P11).
- **D5-06 — Candidate pool spans four families:** (a) issue structure, (b) market regime (NIFTY 3M/6M momentum, India VIX, pipeline density, trailing-N listing gain), (c) DRHP-derived (reuse Phase 2 financials + Phase 3 NLP extraction), (d) anchor-investor demand (the one legitimate T0 demand proxy).
- **D5-07 — Final feature set LEAN (~8–15), interpretable** (SHAP/importance for the model card). Kitchen-sink rejected (overfit risk on ~200–300 rows).
- **D5-08 — Every feature carries a verified `available_at <= T0` timestamp; anchor features carry an EXPLICIT leakage audit** (pre-open anchor allocation only; never post-open subscription). GMP + final subscription multiples excluded. Audit documented in the model card.
- **D5-09 — Abstention = extrapolation + interval-width guard (conformal-native).** Abstain (render the locked "not enough comparable history" note, no band) when features fall outside training support OR the calibrated interval is uselessly wide.
- **D5-10 — Small-N sectors: pool sectors below ~30 IPOs into a pooled 'Other' bucket; report N-per-sector.** Hierarchical/partial-pooling deferred.
- **D5-11 — Displayed per-IPO band = walk-forward as-of-T0 out-of-sample prediction** (model trained only on IPOs that listed before that IPO's T0). Displayed band = backtested band. Leave-one-out and exclude-covered-from-training both rejected.
- **D5-12 — "How this was tested" metrics are GLOBAL walk-forward numbers** (coverage, MAE, per-year RMSE), identical on every IPO page. Per-sector-conditioned metrics rejected (small-N noise).
- **Locked upstream (NOT re-decided):** UI fully locked by `05-UI-SPEC.md`; XGBoost + MAPIE model family + four baselines (predict-zero, global-median, trailing-12-IPO-median, sector-mean) + Diebold–Mariano significance test as the **release gate** (P9); walk-forward only (P4); honest empirical coverage even if it misses 80% (P17). GMP isolation is a hard invariant (D4-03/GMP-02/FCAST-02): the model imports no GMP; the GMP marker is a display-layer read of cached GMP + cached issue price; the forecast render imports no model/training module (pin with an `inspect.getsource` no-model-import audit).

### Claude's Discretion (research/planner territory — this document resolves these)
1. Concrete SEBI/NSE/BSE endpoints + scraping/caching mechanics for the universe build; add a nightly integration test.
2. XGBoost hyperparameters, exact quantile levels, MAPIE conformal variant (CQR split vs CV+/Jackknife+), calibration + PIT-histogram plotting.
3. The `data/forecasts/<drhp_id>.json` record schema (interval bounds, median, global coverage/MAE/per-year-RMSE, abstain flag, as-of/OOS provenance + model version) — **cache-only; UI render imports no model module**.
4. Exact sector taxonomy + the precise small-N pooling threshold (guideline ~30).
5. Diebold–Mariano wiring against the four baselines; the R²>0.5 leakage red-flag check.
6. Empirical tuning of the abstention support/width thresholds.

### Deferred Ideas (OUT OF SCOPE)
- T−1-of-listing model variant (optional model-card sensitivity analysis only).
- Retrospective forecast-vs-actual calibration page (TODOS E7 / Phase 6).
- Chittorgarh JSON API reverse-engineering as a **primary** source (enrichment only).
- Hierarchical / partial-pooling sector model.
- MAAR (market-adjusted) target.
- Full 2014-present universe up front.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **FCAST-01** | Calibrated listing-day return range, 80% prediction interval per covered IPO | §Standard Stack (MAPIE `ConformalizedQuantileRegressor`, `confidence_level=0.8`); §Code Examples "CQR interval"; the per-IPO band is written to `data/forecasts/<drhp_id>.json` (§Forecast Record Schema) |
| **FCAST-02** | Features only `available_at <= T0`; explicit `available_at` enforced; no GMP, no subscription-at-close | §Pattern "available_at feature gate + leakage audit"; §Pitfall 1 (lookahead); D5-01 reconciliation note |
| **FCAST-03** | Walk-forward CV on a survivorship-eliminated SEBI/issuer-side universe (incl. withdrawn/delisted) | §Data Sources (NSE `public-past-issues` + SEBI public-issues + chittorgarh withdrawn report 202); §Pattern "walk-forward as-of-T0"; existing `pipelines/historical/` status taxonomy |
| **FCAST-04** | Forecast page shows empirical coverage, MAE, per-year RMSE | §Pattern "global walk-forward metrics"; §Code Examples "empirical coverage"; written into the record's metrics block |
| **FCAST-05** | Model card committed (data, features, baselines, significance tests, calibration plots, limitations) | §Pattern "model card"; §Calibration diagnostics; §Diebold–Mariano; matplotlib PNG artifacts committed under `/methodology` |
| **GMP-03** | UI shows GMP-vs-GMP-free-model gap as a transparent signal | Display-layer only — §Isolation; the marker reads cached `data/gmp/<drhp_id>.json` + cached issue price (UI-SPEC §GMP-implied-return conversion). No research on the model side (model never sees GMP). |
| **UI-03** | Uncertainty as first-class visual (interval width, GMP-vs-model gap) | UI is CLOSED (`05-UI-SPEC.md`). Research only supplies the record the render reads (§Forecast Record Schema). |
</phase_requirements>

## Summary

Phase 5 is the project's designated non-LLM modeling showcase (P11). The modeling half is well-supported and low-risk in 2026: **MAPIE 1.4.1** ships a first-class `ConformalizedQuantileRegressor` that produces exactly the adaptive-width 80% interval D5-03 requires, and **XGBoost 3.2.0** exposes native quantile regression via `objective="reg:quantileerror", quantile_alpha=…`. The one non-obvious API fact: MAPIE's *non-prefit* CQR path only auto-clones sklearn-family quantile estimators (QuantileRegressor / GradientBoosting / HistGradientBoosting / LGBM) — **XGBoost must use the `prefit=True` path** (train three quantile models yourself, pass them as an ordered list `[lower, upper, median]`, then `conformalize()`). This is the single most important wiring detail on the modeling side.

The genuinely risky half is the **historical universe** (the phase's known blocker, carried from Phase 4's 04-07 checkpoint). The chittorgarh HTML scraper is dead. The durable path in 2026 is a two-source merge: (1) a **listed-universe + issue-price + listing-date** feed from NSE's `public-past-issues` JSON endpoint (best accessed through the maintained `nse` library that handles NSE's cookie/bot-detection), and (2) a **withdrawn/pulled** overlay from SEBI's `/filings/public-issues.html` filings plus chittorgarh's withdrawn-offer-document report (id 202) — without the second source the universe is survivor-only and P3 fails. Listing-day closes and NIFTY/VIX regime features come from the already-installed `jugaad-data` (bhavcopy + `index_df`) with `yfinance` fallback, both already wired in `pipelines/historical/sources.py`.

The honesty keystone (D5-11) is a plain expanding-window walk-forward: order the universe by listing date; for each IPO, train the three quantile models on IPOs that listed before its T0, conformalize on the most-recent-but-still-pre-T0 slice, and emit one out-of-sample band. That band is *simultaneously* the backtest score and the number the UI renders — no second code path. Global coverage, MAE, and per-year RMSE are aggregated over those out-of-sample bands.

**Primary recommendation:** Build as an MVP vertical slice that de-risks data first. Slice 1: assemble a verified ~200–300-IPO panel (NSE past-issues for the listed core + SEBI/chittorgarh-withdrawn overlay for P3) reusing the existing `pipelines/historical/` schema and validator. Slice 2: thinnest end-to-end model — issue-structure features only (D5-06a, no extra scraping) → prefit XGBoost-quantile + MAPIE CQR under expanding-window walk-forward → one committed `data/forecasts/<drhp_id>.json` the UI reads. Slice 3+: add regime/DRHP/anchor features, the four baselines + Diebold–Mariano gate, calibration plots + model card, abstention tuning, then expand N.

## Architectural Responsibility Map

DRHPLens is a single-process Streamlit app with an **offline batch pipeline → committed cache → cache-only render** architecture (the "storage is the integration bus" decision in STATE.md). The relevant "tiers" here are pipeline stages, not network tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Universe assembly (fetch withdrawn+listed, dedupe, status) | Offline pipeline (`pipelines/historical/`) | — | Network + survivorship control belongs off the render path; already the home of the panel schema/validator |
| Listing-day close + return target | Offline pipeline (`sources.fetch_listing_day_close`) | — | Already implemented (jugaad-data → yfinance); reuse `compute_listing_day_return()` |
| Feature engineering + `available_at` gate | Offline pipeline (new `pipelines/features*`) | Phase 2 financials + Phase 3 extraction outputs | Features fuse existing cached DRHP signals; leakage audit is a build-time property |
| Quantile training + CQR conformalization | Offline pipeline (new `pipelines/forecast*`) | MLflow (local file backend) tracks runs | Model is trained once offline; render never trains |
| Walk-forward backtest + metrics | Offline pipeline | MLflow | Global coverage/MAE/RMSE are computed once and baked into every record |
| Per-IPO forecast record | Committed cache (`data/forecasts/<drhp_id>.json`) | — | Mirrors `data/snapshots/` / `data/redflag/` / `data/gmp/` |
| Forecast band render | Streamlit render (`pages/02_snapshot.py` + a `ui/` helper) | cached `data/forecasts/` (read) | Cache-only; imports NO model/training module (isolation invariant) |
| GMP-implied-return marker + gap | Display layer (GMP/display code) | cached `data/gmp/` + cached issue price | Model never sees GMP; conversion is `gmp_₹/issue_price×100` in the display layer only |
| Model card (calibration plot, PIT, baselines, DM, limitations) | Offline artifact → `/methodology` page | matplotlib PNGs committed to repo | FCAST-05; the render just links + embeds committed artifacts |

## Standard Stack

### Core (new Phase 5 dependencies — NONE currently installed in `.venv`)
| Library | Version (verified 2026-07-15) | Purpose | Why Standard |
|---------|-------------------------------|---------|--------------|
| `xgboost` | 3.2.0 latest [VERIFIED: PyPI] | Quantile regressors (`reg:quantileerror`) for lower/median/upper | CLAUDE.md locked model family; native quantile since 2.0; sklearn API (`XGBRegressor`) |
| `mapie` | 1.4.1 latest [VERIFIED: PyPI] | Conformal calibration → adaptive-width 80% interval | CLAUDE.md locked; `ConformalizedQuantileRegressor` is the exact D5-03 primitive [CITED: mapie.readthedocs.io] |
| `scikit-learn` | 1.9.0 latest [VERIFIED: PyPI] | Baselines, pipelines, `train_test_split`, metrics | MAPIE needs sklearn ≥1.3; ubiquitous |
| `mlflow` | 3.14.0 latest [VERIFIED: PyPI] | Local experiment tracking (features, params, backtest splits, calibration) | CLAUDE.md locked; local file backend, commit `mlruns/` |
| `matplotlib` | 3.11.0 latest [VERIFIED: PyPI] | Calibration plot + PIT/reliability histogram PNGs for the model card | Static artifacts committed to repo; no interactivity needed for the card |
| `shap` | 0.51.0 latest [VERIFIED: PyPI] | Feature importance / interpretability for the model card (D5-07) | Standard for tree-model interpretability; supports XGBoost natively |

### Supporting (already installed — reuse, do not re-add)
| Library | Installed | Purpose | Notes |
|---------|-----------|---------|-------|
| `jugaad-data` | 0.33.1 | Listing-day close (bhavcopy) + **NIFTY history** (`index_df` / `NSEIndexHistory`) for regime features + India-VIX | Already in `sources.fetch_listing_day_close`; `index_df` is the NIFTY momentum source (D5-06b). Fragile to NSE changes — nightly integration test. |
| `yfinance` | 1.5.1 (pinned) | Listing-day close fallback (`.NS`/`.BO`) | Already wired as the second price source |
| `requests-cache` | 1.3.3 | Polite cached scraping (IPO history is immutable) | Already the `sources._session()` backend; 1-week expiry |
| `pandas` / `numpy` / `scipy` | 3.0.3 / 2.4.6 / 1.17.1 | Panel + numerics + stats | ⚠️ pandas **3.0** and numpy **2.x** are new — verify the xgboost/mapie/sklearn install resolves cleanly against them in the `.venv` (Python 3.11.15) before building |
| `tenacity` / `beautifulsoup4` / `lxml` / `pyarrow` | installed | Retries / HTML parse / parquet | Existing pipeline deps |

### Optional / evaluate
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `nse` (BennyThadikaran/NseIndiaApi) | 3.1.2 [VERIFIED: PyPI] `[ASSUMED]` provenance | `listPastIPO(from_date, to_date)` / `listCurrentIPO()` / `listUpcomingIPO()` with automatic NSE cookie/bot-handling | Strongest path to the listed-universe feed; alternative is hand-rolled `requests` against the endpoints (§Data Sources). Gate behind a human-verify checkpoint (not in CLAUDE.md's stack). |
| `dieboldmariano` | 1.1.0 [VERIFIED: PyPI] `[ASSUMED]` provenance | `dm_test()` for the P9 significance gate | Niche/low-download; **prefer a ~15-line manual DM** to avoid a fragile dependency (§Diebold–Mariano). |
| `statsmodels` | 0.14.6 | OLS baseline / HAC variance for a manual DM | Only if you want an OLS linear baseline alongside the four locked baselines |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| XGBoost quantile | LightGBM `objective="quantile"` | MAPIE's non-prefit path *does* auto-support `LGBMRegressor` (simpler wiring, no prefit) — but CLAUDE.md locks XGBoost and LightGBM is not installed. Keep XGBoost + prefit. |
| MAPIE CQR (`ConformalizedQuantileRegressor`) | `SplitConformalRegressor` (constant width) | Rejected by D5-03 — constant width undersells heteroscedasticity, the whole point |
| MAPIE CQR | `CrossConformalRegressor` / `JackknifeAfterBootstrapRegressor` (CV+/J+K) | CV+ gives tighter coverage on small N but couples calibration to CV folds, complicating the "displayed band = as-of-T0 backtest band" story (D5-11). Split-CQR-inside-walk-forward is the cleaner honesty narrative. Note CV+ as a model-card sensitivity note if N stays small. |
| `nse` library | Direct `requests` to `nseindia.com/api/public-past-issues` | Direct is one fewer dependency but you re-implement cookie priming + bot-evasion; the library is maintained and already solves this |
| matplotlib | Plotly (already a stated stack lib) | Plotly is for interactive in-app charts; the model card wants committed static PNGs — matplotlib is the lighter fit. Either is defensible. |

**Installation (add to `pyproject.toml` `dependencies`):**
```bash
# core modeling (pin to the CLAUDE.md-locked families; verify resolves vs pandas 3.0 / numpy 2.x)
uv pip install "xgboost>=2.0" "mapie>=1.4,<2" "scikit-learn>=1.5" "mlflow>=2.14" "matplotlib>=3.8" "shap>=0.46"
# universe fetch (gate behind human-verify checkpoint — not in the locked stack)
uv pip install "nse>=3.1"
```

**Version reconciliation (flag for the planner):**
- CLAUDE.md locks "**XGBoost 2.x**" and "**MLflow 2.x**"; the current latest are **XGBoost 3.2.0** and **MLflow 3.14.0**. `reg:quantileerror` is stable and identical in 2.0+ and 3.x; MLflow's local file backend is unchanged across 2.x→3.x. Recommend `xgboost>=2.0` / `mlflow>=2.14` (allow 3.x) and note the CLAUDE.md text predates the 3.x releases. If the user wants a hard pin to 2.x for reproducibility, `xgboost>=2.0,<3` also works — but confirm 2.x wheels build on Python 3.11.15 + numpy 2.x first.

## Package Legitimacy Audit

> slopcheck could not be installed in this environment (`pip install slopcheck` unavailable). Per protocol, **every new external package is tagged `[ASSUMED]`** and the planner MUST gate each install behind a `checkpoint:human-verify` task before it runs. Registry existence (below) is necessary but NOT sufficient.

| Package | Registry | Latest | Source Repo | In CLAUDE.md locked stack? | slopcheck | Disposition |
|---------|----------|--------|-------------|---------------------------|-----------|-------------|
| xgboost | PyPI | 3.2.0 | github.com/dmlc/xgboost | Yes (core) | n/a | Approved — project-locked; verify wheel vs numpy 2.x |
| mapie | PyPI | 1.4.1 | github.com/scikit-learn-contrib/MAPIE | Yes (core) | n/a | Approved — project-locked |
| scikit-learn | PyPI | 1.9.0 | github.com/scikit-learn/scikit-learn | Yes | n/a | Approved — project-locked |
| mlflow | PyPI | 3.14.0 | github.com/mlflow/mlflow | Yes | n/a | Approved — project-locked |
| matplotlib | PyPI | 3.11.0 | github.com/matplotlib/matplotlib | Implied (Plotly listed; matplotlib standard) | n/a | Approved — household package |
| shap | PyPI | 0.51.0 | github.com/shap/shap | Yes (supporting) | n/a | Approved — project-listed |
| nse | PyPI | 3.1.2 | github.com/BennyThadikaran/NseIndiaApi | **No** — new discovery | n/a | **Flagged** — planner inserts `checkpoint:human-verify` before install; discovered via WebSearch, not official docs |
| dieboldmariano | PyPI | 1.1.0 | github.com/edoannunziata/dieboldmariano | **No** — new discovery | n/a | **Flagged / prefer manual** — low-download niche; recommend implementing DM inline instead |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable).
**Packages flagged (planner inserts checkpoint:human-verify before install):** `nse`, `dieboldmariano`. Prefer replacing `dieboldmariano` with a ~15-line inline DM test (§Diebold–Mariano) to reduce attack surface.

## Data Sources (D5-04 — the survivorship-safe universe)

> This is the phase's hard blocker (carried from 04-07). Confidence **MEDIUM** — endpoints are identified and the `nse` library is maintained, but NSE bot-detection and the chittorgarh JSON param-order remain live-fragile. Treat the first live crawl as a checkpoint task, and add the nightly integration test CLAUDE.md requires.

### The two-source merge (P3 survivorship control)
A single "listed IPOs" feed is survivor-only and fails P3. You need **listed core ∪ withdrawn/pulled overlay**, deduped by issuer+issue_date.

**Source A — Listed core (issue price, listing date, symbol) — NSE past issues** [CITED: BennyThadikaran/NseIndiaApi source]
- Endpoint: `https://www.nseindia.com/api/public-past-issues` (also `…/all-upcoming-issues?category=ipo` and `…/ipo-current-issue` for open/upcoming coverage). `[VERIFIED: NseIndiaApi NSE.py]`
- Access: NSE blocks bare requests. Prime cookies by GETting an NSE HTML page (e.g. the quotes/option-chain page) with a realistic browser User-Agent + `Referer`, persist the cookie jar, then hit the `/api/...` JSON. The `nse` library (`NSE.listPastIPO(from_date, to_date)`) does exactly this and caches cookies to disk — **strongly prefer it over hand-rolling**. `[CITED: nse 3.1.x docs]`
- Returns per-IPO dicts with issue price / listing date / symbol / series (exact field names to be confirmed on first live pull — snapshot the raw JSON alongside the parsed rows, matching the existing "save raw HTML" defensive posture).

**Source B — Withdrawn/pulled overlay (the P3 control) — SEBI + chittorgarh-withdrawn**
- SEBI filings: `https://www.sebi.gov.in/filings/public-issues.html` and the listing action `…/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10` — month-bucketed DRHP filings, each carrying a status; the issuer-side record of documents filed (including those that never listed). No clean API; HTML-tolerant scrape + save-raw. `[CITED: sebi.gov.in/filings/public-issues.html]`
- chittorgarh withdrawn report: `https://www.chittorgarh.com/report/ipo-drhp-offer-document-withdrawn/202/` — a curated list of withdrawn/cancelled offer documents. `[CITED: chittorgarh.com report 202]` Note the current report page states coverage "from 1 April 2025 onwards" for the newest slice — **coverage before 2025 is uncertain**; SEBI filings are the authoritative pre-2025 withdrawn source.

**Listing-day close + return** — already implemented, reuse verbatim:
- `pipelines/historical/sources.fetch_listing_day_close()` → jugaad-data bhavcopy (`stock_df`) primary, `yfinance` `.NS`/`.BO` fallback, returns `None`→NaN (retained) on miss. Feed into the existing `compute_listing_day_return()`.

**Regime features (D5-06b)** — sourced offline, snapshotted as-of T0:
- NIFTY 50 3M/6M momentum: `jugaad_data.nse.index_df` / `NSEIndexHistory` (installed). India VIX history: NSE (via `nse` library or NSE archives). Pipeline density / trailing-N listing gain: derived from the panel itself (count of IPOs in a trailing window; mean of trailing-N listing gains) — **compute strictly from IPOs with listing_date < T0** (no lookahead).

### chittorgarh JSON API (DEMOTED to enrichment — D5-04)
- Lead: `https://webnodejs.chittorgarh.com/cloud/report/data-read/83/…` returns `HTTP 200 application/json` (report 83 = mainboard IPO list; 202 = withdrawn; 158 = upcoming DRHP-filed; 82 = all main+SME). `[CITED: data/historical/README.md 04-07 note]`
- **UNVERIFIED:** the exact path-segment order (`page/size/year/FY/type`) is built in the site's JS bundle, not the server HTML; a guessed `.../83/1/5/2026/2025-26/0/all` returned `{"msg":-1,"error":"No data found."}`. To use it, capture the real request from the browser Network tab and pin the working param string. **Do not** rely on this as the primary path (per D5-04); it is a cross-check only. Confidence **LOW**.

### Reuse the existing pipeline scaffolding (do not rebuild)
- `pipelines/historical/__init__.py` — `PANEL_COLUMNS`, `STATUS_VALUES` (the P3 taxonomy: withdrawn/listed_alive/delisted/merged/name_changed), `compute_listing_day_return()`, `assemble_panel()` (validates status, replace-with-NaN, never drops).
- `pipelines/historical/sources.py` — `ALLOWED_HOSTS` SSRF allow-list (**must extend** to add `www.nseindia.com` and confirm SEBI/NSE-archives hosts), typed coercion helpers, cached polite session. **`fetch_chittorgarh_index` is the dead selector to replace** — repoint Source A to NSE past-issues, add a SEBI/withdrawn fetcher for Source B.
- `pipelines/historical/validate.py` — the ~7% median-MAAR divergence flag (survivor-inflation guard). Run it on the real panel; a median >20% is the survivorship red flag.
- `pipelines/historical/build.py` — `build` (live) vs `build-sample` (offline) CLI; extend the live path to the two-source merge.

## Architecture Patterns

### System Architecture Diagram

```
                         OFFLINE BATCH PIPELINE (network; run at checkpoints)
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  Source A: NSE /api/public-past-issues ─┐                                       │
  │  (listed core: price, listing date)      │  merge + dedupe                      │
  │                                          ├──► assemble_panel() ──► ipo_panel.*  │
  │  Source B: SEBI public-issues filings ───┤   (status taxonomy,   (parquet+csv,  │
  │  + chittorgarh withdrawn (id 202)        │    replace-with-NaN)   survivorship) │
  │  (withdrawn/pulled overlay — P3)        ─┘          │                           │
  │  jugaad-data bhavcopy / yfinance ──► listing_day_close ──► compute_return()     │
  │                                                     │                           │
  │            ┌────────────────────────────────────────┘                          │
  │            ▼                                                                    │
  │   FEATURE BUILD  (available_at <= T0 gate; leakage audit)                       │
  │   (a) issue structure  (b) NIFTY/VIX regime  (c) DRHP financials+NLP  (d) anchor│
  │            │  each feature stamped available_at; anchor = pre-open alloc only   │
  │            ▼                                                                    │
  │   WALK-FORWARD LOOP  (order by listing_date; expanding window)                  │
  │   for each IPO i:                                                               │
  │     train pool = {IPOs listed before T0_i}                                      │
  │       ├─ proper-train (older slice) → 3× XGBRegressor(reg:quantileerror)        │
  │       │                                q=0.1 (low), 0.9 (high), 0.5 (median)    │
  │       └─ calib slice (newer, still < T0_i) → CQR.conformalize()                 │
  │     predict_interval(x_i) ─► (low_i, median_i, high_i)  [OUT-OF-SAMPLE]         │
  │            │                                                                    │
  │            ├─► aggregate ─► GLOBAL coverage · MAE · per-year RMSE (D5-12)        │
  │            ├─► 4 baselines (as-of-T0) + Diebold–Mariano gate (P9)               │
  │            └─► calibration plot + PIT/reliability + SHAP  ──► MODEL CARD (PNGs)  │
  │            │        (MLflow tracks every run)                                    │
  │            ▼                                                                    │
  │   WRITE  data/forecasts/<drhp_id>.json  (per covered IPO: band = its OOS band + │
  │          global metrics + abstain flag + as-of/OOS provenance + model_version)  │
  └──────────────────────────────────────────────────────────────────────────────┘
                                     │  (committed cache — the integration bus)
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  STREAMLIT RENDER (cache-only; imports NO model/training module)                │
  │  pages/02_snapshot.py:  … _render_peer_block()                                  │
  │        └─► NEW forecast block (after peer, before ranked-risks — L5-4)          │
  │              reads data/forecasts/<drhp_id>.json  ──► band/median/0%/metrics    │
  │              reads data/gmp/<drhp_id>.json + issue price ──► GMP marker (display)│
  │        … ranked-risks … GMP block (still last) … Q&A chat                        │
  │  pages/01_methodology.py:  model-card section (embeds committed PNGs + DM table)│
  └──────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (new files; mirror existing conventions)
```
pipelines/
├── historical/            # EXISTS — extend Source A/B; keep schema/validator
├── features/              # NEW — feature build + available_at gate + leakage audit
│   ├── __init__.py        #   FEATURE_SPECS: each feature -> available_at rule
│   └── build.py           #   assemble feature matrix from panel + Phase2/3 caches
├── forecast/              # NEW — the model + walk-forward + record writer
│   ├── __init__.py        #   load_forecast(drhp_id) -> ForecastRecord (cache read)
│   ├── model.py           #   3× XGB quantile + MAPIE CQR (prefit) wrapper
│   ├── walkforward.py     #   expanding-window as-of-T0 loop -> OOS bands + metrics
│   ├── baselines.py       #   4 baselines (as-of-T0) + Diebold–Mariano gate
│   ├── diagnostics.py     #   coverage/MAE/RMSE, calibration plot, PIT, SHAP (PNGs)
│   └── precompute.py      #   typer CLI: write data/forecasts/<id>.json per catalogue IPO
data/forecasts/            # NEW cache kind (mirror data/snapshots|redflag|gmp)
ui/forecast_block.py       # NEW — cache-only render helper (NO model import)
model_card/                # NEW — committed MODEL_CARD.md + PNGs (FCAST-05 artifact)
tests/unit/
├── test_forecast_isolation.py   # NEW — mirror test_gmp_isolation.py (reverse audit)
├── test_walkforward_no_lookahead.py  # NEW — assert train set ⊂ {listing<T0_i}
├── test_forecast_schema.py      # NEW — record round-trip + abstain states
└── test_features_available_at.py# NEW — every feature has available_at <= T0
```

### Pattern 1: XGBoost-quantile + MAPIE CQR via the **prefit** path (D5-03)
**What:** Three XGBoost quantile regressors → wrap in MAPIE `ConformalizedQuantileRegressor(prefit=True)` → adaptive-width 80% interval.
**When to use:** Always here — XGBoost is NOT in MAPIE's non-prefit auto-support list, so prefit is mandatory.
**Critical detail:** the prefit estimator list order is **`[lower, upper, median]`** (0.1, 0.9, 0.5), NOT ascending. `confidence_level=0.8` ⇒ underlying quantiles 0.1 / 0.5 / 0.9.
```python
# Source: mapie.readthedocs.io ConformalizedQuantileRegressor + xgboost.readthedocs.io quantile_regression
from xgboost import XGBRegressor
from mapie.regression import ConformalizedQuantileRegressor

def make_quantile_models(X_tr, y_tr, params):
    common = dict(objective="reg:quantileerror", tree_method="hist", **params)
    m_low = XGBRegressor(quantile_alpha=0.1, **common).fit(X_tr, y_tr)
    m_high = XGBRegressor(quantile_alpha=0.9, **common).fit(X_tr, y_tr)
    m_med  = XGBRegressor(quantile_alpha=0.5, **common).fit(X_tr, y_tr)
    return [m_low, m_high, m_med]                     # ORDER: lower, upper, median

def fit_cqr(models, X_cal, y_cal):
    cqr = ConformalizedQuantileRegressor(
        estimator=models, confidence_level=0.8, prefit=True,
    )
    cqr.conformalize(X_cal, y_cal)                    # calibration set (still < T0_i)
    return cqr

# predict for one held-out IPO
points, intervals = cqr.predict_interval(X_i)         # intervals shape (n, 2, 1)
low  = intervals[:, 0, 0]                             # per-IPO lower bound
high = intervals[:, 1, 0]                             # per-IPO upper bound (adaptive width)
median = points                                       # faint-tick value for the UI
```
**Anti-pattern:** passing a single `XGBRegressor` to `ConformalizedQuantileRegressor(prefit=False)` — MAPIE won't know how to clone-and-set the quantile for XGBoost (only QuantileRegressor/GradientBoosting/HistGradientBoosting/LGBM are auto-supported). It will fail or misbehave.

### Pattern 2: Expanding-window walk-forward = "displayed band = backtested band" (D5-11, P4)
**What:** One pass over the universe ordered by `listing_date`; each IPO gets exactly one out-of-sample band, which is both the backtest observation and the committed record.
**The load-bearing subtlety — the calibration set:** CQR needs a conformalization set **disjoint from the quantile-training set AND entirely before T0_i**. So split the pre-T0 pool by listing date into an older *proper-train* slice and a newer *calibration* slice; both remain strictly before the target's T0.
```python
# Source: reasoning from MAPIE split-CQR + CLAUDE.md "walk-forward by listing date"
rows = panel.dropna(subset=["listing_day_return"]).sort_values("listing_date")
MIN_TRAIN = 60            # abstain until enough prior IPOs (tune; D5-09)
CAL_FRAC  = 0.25          # newest 25% of the pre-T0 pool is the calibration set
records = []
for i, ipo in rows.iterrows():
    pool = rows[rows["listing_date"] < ipo["issue_date"]]   # T0 = issue-open (D5-01)
    if len(pool) < MIN_TRAIN:
        records.append(abstain_record(ipo, reason="insufficient_history")); continue
    cut = pool["listing_date"].quantile(1 - CAL_FRAC)
    tr, cal = pool[pool.listing_date <= cut], pool[pool.listing_date > cut]
    models = make_quantile_models(X[tr.index], y[tr.index], PARAMS)
    cqr = fit_cqr(models, X[cal.index], y[cal.index])
    pts, iv = cqr.predict_interval(X[[i]])
    records.append(oos_record(ipo, low=iv[0,0,0], high=iv[0,1,0], median=pts[0]))
# GLOBAL metrics over records (D5-12): coverage, MAE, per-year RMSE
```
**Why not `sklearn.TimeSeriesSplit`:** it yields contiguous *folds*, not a per-IPO *as-of* prediction; you'd lose the exact D5-11 "one OOS band per IPO." A custom loop is clearer and provably lookahead-free. **Never** `KFold`/`train_test_split(shuffle=True)` (CLAUDE.md "What NOT to Use").
**Efficiency:** ~200–300 IPOs × 3 small XGB fits = seconds–minutes offline. If it gets slow when N expands, refit on a cadence (e.g. every N new listings) rather than per-IPO — but the honest default is per-IPO as-of refit.

### Pattern 3: `available_at <= T0` feature gate + leakage audit (FCAST-02, P4, D5-08)
**What:** Each feature declares an `available_at` rule; the builder asserts `available_at <= T0` (issue-open) for every feature of every row and records the audit for the model card.
| Family | Example features | `available_at` | Verdict |
|--------|------------------|----------------|---------|
| (a) Issue structure | issue size ₹, price-band width %, OFS/fresh split, promoter dilution %, lot size | DRHP/RHP filing date | ≤ T0 ✓ |
| (b) Regime | NIFTY 3M/6M momentum, India VIX, pipeline density, trailing-N listing gain | T0−1 EOD snapshot | ≤ T0 ✓ (snapshot as-of T0) |
| (c) DRHP-derived | revenue growth, margins, RoE, debt (Phase 2); red-flag count, RPT %, use-of-proceeds mix, promoter holding (Phase 3) | prospectus filing | ≤ T0 ✓ |
| (d) Anchor demand | anchor book size, anchor-investor quality, lock-in | anchor allocation disclosed **T0−1** | ≤ T0 ✓ **BORDERLINE — audit** |
| EXCLUDED | GMP; final/at-close subscription multiples; any listing-day price | > T0 or compliance-barred | ✗ never a feature |
**Anchor leakage audit (D5-08):** anchor allocation is published the day before issue open, so it is legitimately ≤ T0 — but you must read *only the pre-open allocation*, never the post-open QIB/NII/RII subscription that closes after T0. Document, in the model card, exactly which anchor field was used and its disclosure timestamp.
**R²>0.5 red-flag check (P4):** compute walk-forward OOS R² of the median prediction; **R² > 0.5 fires a leakage alarm** in the model-card build (a pre-apply, no-demand model should be humble — a high R² almost always means a T0-violating feature slipped in). This is an automated gate, not just prose.

### Pattern 4: Four baselines + Diebold–Mariano release gate (P9)
**What:** Every baseline is scored **under the same walk-forward as-of-T0 protocol** as the model, then DM-tested. See §Diebold–Mariano.

### Pattern 5: Cache-only forecast record + isolation audit (D5-11, GMP/model isolation)
See §Forecast Record Schema and §Isolation.

### Anti-Patterns to Avoid
- **Leave-one-out / shuffled CV** for the displayed band — reintroduces future data (rejected in D5-11; violates P4).
- **Calibration set overlapping the training set** — invalidates the conformal coverage guarantee (silent P17 failure).
- **Rounding empirical coverage to 80%** — UI-SPEC + P17 forbid it; show the real held-out number.
- **Any GMP or subscription-at-close feature** — compliance + circularity + isolation invariant.
- **Training/predicting at render time** — the render is cache-only; no model import (isolation test).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conformal 80% interval | Custom residual-quantile calibration | MAPIE `ConformalizedQuantileRegressor` | Correct split-CQR math, adaptive width, marginal-coverage guarantee — the exact D5-03 artifact |
| Quantile regression | Custom pinball-loss training loop | XGBoost `reg:quantileerror` + `quantile_alpha` | Native since 2.0; sklearn API; no custom gradients |
| NSE cookie/bot handling | Hand-rolled cookie priming | `nse` library (or copy its priming approach) | NSE actively blocks bare requests; the library already solves cookie refresh + retry |
| Listing-day close | New bhavcopy scraper | existing `sources.fetch_listing_day_close` | jugaad-data→yfinance fallback already implemented, tested-offline, replace-with-NaN honest |
| Panel schema / survivorship | New dataframe schema | existing `pipelines/historical/` (`assemble_panel`, `STATUS_VALUES`, validator) | Survivorship taxonomy + MAAR divergence flag already built and unit-tested |
| Cache read/write + allow-list | New JSON I/O | mirror `pipelines/snapshot.py` / `redflag.py` `load_*`/`precompute` + `is_known_drhp_id` gate | Established pattern; path-traversal-safe; per-IPO failure isolation |
| Empirical coverage | (borderline) | `np.mean((y>=low)&(y<=high))` — a one-liner — OR `mapie.metrics` | Coverage is trivial; a manual line avoids MAPIE-metrics import-path churn (see Open Questions) |
| Feature importance | Custom gain parsing | `shap` (XGBoost-native) | Model-card interpretability with consistent Shapley values |

**Key insight:** Almost the entire modeling stack is a thin composition of mature libraries; the *only* things worth hand-writing are the walk-forward loop (must match D5-11 exactly), the `available_at` gate (project-specific leakage rules), and the record schema. Spend the modeling budget there, not on re-deriving conformal math.

## Runtime State Inventory

> Phase 5 is greenfield modeling on top of existing caches — not a rename/refactor. This inventory covers the state a *fresh universe build* touches, since that is the operational risk.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/historical/ipo_panel.{parquet,csv}` currently hold the **7-row fictional SAMPLE**, not real data. `data/forecasts/` does not exist yet. | Build the real panel (Slice 1); create `data/forecasts/`. Commit both. |
| Live service config | None. No live service holds Phase-5 state. The universe fetch hits NSE/SEBI/chittorgarh but caches to `.cache/historical_http` (requests-cache SQLite, 1-week TTL). | Extend `ALLOWED_HOSTS` to include `www.nseindia.com` (SSRF control); confirm SEBI host. |
| OS-registered state | None. No scheduled tasks. CLAUDE.md asks for a **nightly integration test** for NSE endpoints — that is a new CI job to add, not existing state. | Add nightly integration test (GitHub Actions) hitting the live NSE past-issues endpoint. |
| Secrets/env vars | None new. Universe/price sources are keyless public endpoints. (Distinct from Phase 3's `GEMINI_API_KEY`/`QDRANT_*`, which Phase 5 does not use.) | None. |
| Build artifacts / installed packages | `.venv` (Python 3.11.15) is **missing** xgboost/mapie/scikit-learn/mlflow/matplotlib/shap. `nse` not installed. MLflow will create `mlruns/`. | Add deps to `pyproject.toml`; commit `mlruns/` per CLAUDE.md deploy plan; add `data/forecasts/` + `model_card/`. |

**Nothing found in category:** Live service config, OS-registered state, and secrets are all "None" for Phase 5 as verified above.

## Common Pitfalls

### Pitfall 1: Lookahead / leakage (P4) — the one that silently invalidates everything
**What goes wrong:** A feature or calibration row from after T0 leaks into training; OOS metrics look great, R² jumps past 0.5, the interval is falsely tight.
**Why it happens:** shuffled CV; a regime feature snapshotted after issue-open; anchor field that is actually post-open subscription; calibration set drawn from the whole panel.
**How to avoid:** the expanding-window loop (Pattern 2) with the calibration slice kept strictly before T0_i; the `available_at` gate (Pattern 3); a unit test asserting `train.listing_date.max() < ipo.issue_date` for every fold; the **R²>0.5 automated alarm**.
**Warning signs:** OOS R² > 0.5; coverage far above 80% with a suspiciously narrow interval; the model "beats" the trailing-median baseline by a large, significant margin.

### Pitfall 2: Regime-shift blindness (P6)
**What goes wrong:** 2021 bull-market listing pops train a model that is overconfident in a 2022–2023 cooler regime; per-year RMSE hides in a global average.
**How to avoid:** include regime features (NIFTY momentum, India VIX, pipeline density, trailing-N listing gain, D5-06b); report **per-year RMSE** (D5-12) so regime dependence is visible; conformal width should widen in volatile regimes if the quantile models are honest.
**Warning signs:** flat global RMSE but one year's RMSE 2–3× the others.

### Pitfall 3: Small-N sector slices (P7)
**What goes wrong:** a sector with 4 IPOs gets a "sector-mean" feature/baseline that is pure noise.
**How to avoid:** pool sectors below ~30 IPOs into `Other` (D5-10); **report N-per-sector**; keep metrics GLOBAL (D5-12), never per-sector-conditioned in the UI.
**Warning signs:** sector-mean baseline wildly unstable across walk-forward steps.

### Pitfall 4: Naive baselines beat the model (P9) — and that might be the honest truth
**What goes wrong:** a pre-apply, no-demand model genuinely may not beat "trailing-12-IPO-median" — and if you don't test, you ship a model that adds nothing.
**How to avoid:** score all four baselines under the same walk-forward; DM-test the loss differentials; make "model significantly beats baselines" a **release gate** — but if it doesn't, the honest model card says so (low R² is a feature, D5-01/specifics). Do not p-hack features to cross the gate.
**Warning signs:** DM p-value oscillates around 0.05; tiny MAE improvement over global-median.

### Pitfall 5: Calibration theater (P17)
**What goes wrong:** parametric "coverage" reported on training data; coverage silently rounded to the 80% target.
**How to avoid:** empirical coverage computed **only on the held-out OOS bands** (conformal, not parametric); show the real number even at 74% or 86%; commit the calibration/reliability plot + PIT diagnostic.
**Warning signs:** coverage exactly 80.0%; coverage measured before the calibration split.

### Pitfall 6: UX implies advice (P21) — owned but display-side
**What goes wrong:** a big median headline / green-up styling reads as "buy."
**How to avoid:** the UI-SPEC already forbids this (band width dominant, faint median tick, no green/red, banned-token scrubber). Research-side: the record must supply the *band*, not a "prediction" the render could accidentally headline. Keep `median` a Small-annotation value, never the record's headline field.

### Pitfall 7: NSE/chittorgarh source fragility (operational)
**What goes wrong:** NSE rotates bot-detection or the JSON shape; a silent 0-row build (exactly the 04-07 failure).
**How to avoid:** use the maintained `nse` library; save raw JSON alongside parsed rows; run `validate.sanity_check_median` (a >20% median or all-`listed_alive` status distribution is the survivorship alarm); **nightly integration test**; a non-zero-row assertion in the build.
**Warning signs:** `Wrote 0 rows`; status distribution with zero `withdrawn`/`delisted`; median MAAR way above band.

## Code Examples

### Empirical coverage, MAE, per-year RMSE (D5-12, FCAST-04)
```python
# Source: standard conformal metrics; manual coverage avoids MAPIE-metrics import-path churn
import numpy as np, pandas as pd
def global_metrics(df):  # df: one row per OOS IPO with actual, low, high, median, listing_year
    covered = (df.actual >= df.low) & (df.actual <= df.high)
    coverage = float(covered.mean())                      # show REAL number (P17)
    mae = float((df.actual - df.median).abs().mean())
    per_year_rmse = (df.assign(se=(df.actual - df.median) ** 2)
                       .groupby("listing_year").se.mean().pow(0.5).round(2).to_dict())
    mean_width = float((df.high - df.low).mean())
    return dict(coverage=coverage, mae=mae, per_year_rmse=per_year_rmse,
                mean_width=mean_width, n=len(df))
```

### Four baselines, scored as-of-T0 (P9)
```python
# Source: reasoning from ROADMAP P9 baseline list; all computed inside the same walk-forward loop
def baselines_asof(pool, sector):                          # pool = IPOs listed < T0_i
    y = pool.listing_day_return.dropna()
    return {
        "predict_zero":     0.0,
        "global_median":    float(y.median()),
        "trailing_12":      float(pool.sort_values("listing_date").listing_day_return
                                      .dropna().tail(12).median()),
        "sector_mean":      float(pool.loc[pool.sector == sector, "listing_day_return"]
                                      .dropna().mean()),    # 'Other'-pooled sector (D5-10)
    }
```

### Diebold–Mariano (inline; avoids the `dieboldmariano` dependency)
```python
# Source: Diebold & Mariano (1995); Harvey small-sample correction. Applied to per-IPO
# absolute-error differentials ORDERED BY LISTING DATE (see caveat in Open Questions).
import numpy as np
from scipy.stats import t as student_t
def dm_test(e_model, e_base, h=1):
    d = np.abs(e_model) - np.abs(e_base)                   # loss differential (MAE loss)
    n = len(d); dbar = d.mean()
    gamma0 = np.var(d, ddof=0)
    var_dbar = gamma0 / n                                   # h=1 => no autocovariance terms
    dm = dbar / np.sqrt(var_dbar)
    p = 2 * (1 - student_t.cdf(abs(dm), df=n - 1))
    return dm, p       # dm<0 & p<0.05 => model's loss significantly LOWER than baseline
```

### Forecast record write (mirror `pipelines/snapshot.py`)
```python
# Source: mirror of pipelines/snapshot.py load/precompute + data/catalogue_loader allow-list
import json, datetime as dt
from pathlib import Path
from data.catalogue_loader import is_known_drhp_id
FORECASTS_DIR = Path(__file__).resolve().parents[2] / "data" / "forecasts"
def load_forecast(drhp_id: str) -> dict:
    if not is_known_drhp_id(drhp_id):                      # T-0X path-traversal gate
        raise ValueError(f"unknown drhp_id={drhp_id!r}")
    p = FORECASTS_DIR / f"{drhp_id}.json"
    if not p.exists():
        raise FileNotFoundError(p)                          # -> UI empty-state (not covered)
    return json.loads(p.read_text("utf-8"))
```

## Forecast Record Schema (`data/forecasts/<drhp_id>.json`, cache-only)

Recommended shape (planner may refine field names; keep it flat, no model objects, no GMP):
```jsonc
{
  "drhp_id": "swiggy_2024_11",
  "computed_at": "2026-07-15T00:00:00Z",
  "model_version": "cqr-xgb-2026.07-v1",     // pin the model+feature-set version
  "as_of_listing_date": "2024-11-13",        // the T0 used; provenance for D5-11
  "out_of_sample": true, "walk_forward": true,
  "abstain": false, "abstain_reason": null,   // "insufficient_history" | "out_of_support" | "interval_too_wide"
  "interval": { "low_pct": -4.2, "high_pct": 21.7, "median_pct": 6.1, "width_pts": 25.9 },
  "sector": "Other",                          // pooled per D5-10
  "metrics": {                                // GLOBAL walk-forward numbers (D5-12) — identical on every IPO
    "coverage_empirical": 0.783, "mae_pts": 11.4,
    "backtest_window": "2016-2025", "n": 247,
    "per_year_rmse": { "2016": 14.1, "2017": 12.8, "…": 0.0 }
  }
}
```
**Abstention states (D5-09) map to the UI-SPEC empty states:** `abstain:true` → the locked "not enough comparable history to calibrate an honest range" note (no band). Missing file → "no calibrated forecast available yet." Never fabricate an interval or a metric.

## Isolation (the hard invariant — GMP-02 / D4-03 / FCAST-02)

Mirror `tests/unit/test_gmp_isolation.py` in **reverse**, at both boundaries:
1. **Render must not import the model.** New `tests/unit/test_forecast_isolation.py`: `inspect.getsource` the forecast render module (`ui/forecast_block.py` + its call site in `pages/02_snapshot.py`) and assert none of `{"xgboost","mapie","sklearn","conformal","pipelines.forecast","pipelines.features","pipelines.historical","shap"}` appear. The render reads only `data/forecasts/` + `data/gmp/` JSON.
2. **Predictor must not import GMP.** The existing `test_gmp_isolation.py` docstring already reserves this: assert `pipelines.forecast.*` / `pipelines.features.*` source contains no `pipelines.gmp` / `gmp` reference (the model never sees GMP).
3. **GMP marker is display-layer.** The `gmp_implied_return = gmp_₹ / issue_price × 100` conversion lives with the GMP/display code (reads cached `data/gmp/<drhp_id>.json` + cached issue price via `ui/format_inr.py`), never as a model feature.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MAPIE `MapieQuantileRegressor` (0.x, `alpha` at predict time) | MAPIE `ConformalizedQuantileRegressor` with `fit → conformalize → predict_interval`, `confidence_level` at init | MAPIE 1.0 (2025) | The CONTEXT/CLAUDE stack text implies the old class; **use the 1.x class + workflow** [CITED: mapie v1 release notes] |
| XGBoost with no quantile loss (custom objective) | Native `objective="reg:quantileerror"`, `quantile_alpha` | XGBoost 2.0 | Three-line quantile models; no custom gradients [CITED: xgboost quantile_regression docs] |
| chittorgarh HTML `<table>` scrape | Next.js app; scrape returns 0 rows | ~2026-07-07 | `fetch_chittorgarh_index` is dead — pivot to NSE past-issues + SEBI (D5-04) |
| `nsepy` for NSE | `jugaad-data` (installed) + `nse` library | ongoing | nsepy is dead (CLAUDE.md "What NOT to Use") |

**Deprecated/outdated:**
- `MapieQuantileRegressor`, `MapieRegressor` monolith, and `alpha`-at-predict — replaced in MAPIE 1.x by `ConformalizedQuantileRegressor` / `SplitConformalRegressor` / `CrossConformalRegressor` / `JackknifeAfterBootstrapRegressor` + `confidence_level`.
- `pipelines/historical/sources.fetch_chittorgarh_index` — stale selector; retire as primary (D5-04).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NSE `public-past-issues` JSON returns issue price + listing date per IPO with field names the parser can map | §Data Sources | MEDIUM — field names unconfirmed until first live pull; save raw JSON to de-risk |
| A2 | The `nse` library reliably handles NSE cookie/bot-detection in July 2026 | §Data Sources, §Package Audit | MEDIUM — NSE can change detection; nightly integration test + `nse` maintenance cadence mitigate |
| A3 | SEBI `/filings/public-issues.html` + chittorgarh report 202 together give adequate pre-2025 withdrawn/pulled coverage | §Data Sources | MEDIUM-HIGH — chittorgarh-202 may only cover 2025+; if SEBI pre-2025 coverage is thin, the ~200–300 verified slice may under-represent withdrawals (weakens P3). Validate withdrawn-count in the built panel. |
| A4 | chittorgarh `webnodejs data-read/83` param order is discoverable from the browser Network tab | §Data Sources | LOW impact — demoted to enrichment; not on the critical path |
| A5 | `mapie.metrics` coverage import path in 1.4.1 is `regression_coverage_score` (path may be `mapie.metrics.regression`) | §Code Examples | LOW — mitigated by the one-line manual coverage (recommended anyway) |
| A6 | XGBoost 3.2.0 (and/or 2.x) wheels install cleanly against pandas 3.0 / numpy 2.4 on Python 3.11.15 | §Standard Stack | MEDIUM — very new pandas/numpy; resolve the install in the `.venv` before Slice 2. Fallback: pin numpy/pandas compatible versions if a conflict appears. |
| A7 | Applying the Diebold–Mariano test to per-IPO loss differentials ordered by listing date is an acceptable operationalization | §Diebold–Mariano, Open Questions | MEDIUM — DM assumes a time series of forecast errors; IPO returns are cross-sectional. Defensible but arguable; document the choice in the model card. |
| A8 | A genuine PIT histogram is derivable from a quantile grid; with only 3 quantiles a reliability curve is the honest substitute | §Calibration diagnostics, Open Questions | MEDIUM — the UI-SPEC literally names "PIT histogram"; may need a small quantile grid (0.05…0.95) as an extra model-card diagnostic |

## Open Questions

1. **PIT histogram vs reliability curve (P17, FCAST-05).**
   - What we know: a true PIT needs a predictive CDF; CQR gives 3 quantiles for the production interval. The UI-SPEC names "PIT histogram" explicitly.
   - What's unclear: whether to (a) train a separate quantile grid (0.05,0.1,…,0.95) purely for the PIT/reliability diagnostic, or (b) relabel the artifact a "coverage reliability diagram."
   - Recommendation: do (a) as a model-card-only diagnostic (cheap; a dozen extra quantile fits on the final walk-forward), keep the production interval at 0.1/0.5/0.9. Flag in the model card that PIT is derived from the grid, not the production interval.

2. **Diebold–Mariano on cross-sectional IPO returns (P9).**
   - What we know: DM is designed for time-ordered forecast-error series; IPO listing-day returns are a cross-section ordered only by listing date.
   - What's unclear: whether the reviewer audience expects DM specifically or would accept a paired test (Wilcoxon signed-rank / paired t on absolute errors).
   - Recommendation: report DM (ordered by listing date) since ROADMAP/CONTEXT lock it, AND a paired Wilcoxon as a robustness check in the model card. Note the caveat (A7).

3. **CQR variant if N stays small (~200–300).**
   - What we know: split-CQR "wastes" ~25% of the pre-T0 pool on calibration each step; CV+/Jackknife+ use data more efficiently.
   - What's unclear: whether split-CQR calibration sets get too thin for the earliest IPOs.
   - Recommendation: ship split-CQR (cleanest D5-11 story); add a model-card sensitivity note comparing coverage under `CrossConformalRegressor` if early-window coverage is unstable. Tune `MIN_TRAIN` / `CAL_FRAC` empirically (D5-09 territory).

4. **Sector taxonomy source (D5-10).**
   - What we know: sector must come from somewhere at T0 (DRHP industry classification, or an exchange/industry mapping).
   - What's unclear: no single clean sector field exists in the current panel schema.
   - Recommendation: derive a coarse sector from the DRHP (Phase 2/3 extraction) or a simple issuer→sector map; pool <30-IPO sectors into `Other`; this is a Slice-3 concern, not a blocker for the thin slice.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.11 venv | everything | ✓ | 3.11.15 | — |
| pandas / numpy / scipy | panel + modeling | ✓ | 3.0.3 / 2.4.6 / 1.17.1 | — (⚠ verify xgb/mapie compat, A6) |
| jugaad-data | listing close + NIFTY regime | ✓ | 0.33.1 | yfinance |
| yfinance | listing close fallback | ✓ | 1.5.1 | — |
| requests-cache / tenacity / bs4 / lxml | polite scrape | ✓ | installed | — |
| pyarrow | parquet panel | ✓ | 24.0.0 | CSV mirror |
| **xgboost** | quantile models | ✗ | — | none — must install (locked stack) |
| **mapie** | conformal interval | ✗ | — | none — must install (locked stack) |
| **scikit-learn** | baselines/metrics | ✗ | — | none — must install |
| **mlflow** | experiment tracking | ✗ | — | degrade: log to a local JSON if omitted |
| **matplotlib** | calibration/PIT PNGs | ✗ | — | Plotly (already stack) static export |
| **shap** | model-card importance | ✗ | — | XGBoost `feature_importances_` (weaker) |
| **nse** (NseIndiaApi) | listed-universe fetch | ✗ | — | hand-rolled `requests` + cookie priming |
| **Network egress to NSE/SEBI/chittorgarh** | universe build (FCAST-03) | ✗ (sandbox) | — | **BLOCKING** — deferred to a live checkpoint task, as in 04-07 |

**Missing dependencies with no fallback (planner must address):**
- xgboost, mapie, scikit-learn — add to `pyproject.toml`, install in `.venv`, resolve any pandas-3.0/numpy-2.x conflict (A6).
- **Live network egress for the universe crawl** — the same blocker as 04-07. Slice 1's live build is a human/network **checkpoint task**, not an executor-sandbox step. Unit-test everything offline (monkeypatch fetchers) exactly as `pipelines/snapshot.py` / `redflag.py` do.

**Missing dependencies with fallback:** mlflow (JSON log), matplotlib (Plotly), shap (native importances), nse (hand-rolled requests).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is REQUIRED. The historical-universe network step is a hard blocker, so validation must be derivable offline (monkeypatched fetchers), matching the proven Phase 2/3/4 posture.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (`[tool.pytest.ini_options]`, `timeout=60`, strict markers) |
| Config file | `pyproject.toml` (+ `tests/conftest.py`, `tests/unit/conftest.py` exist) |
| Quick run command | `.venv/bin/python -m pytest tests/unit -q` |
| Full suite command | `.venv/bin/python -m pytest tests -q` |
| Live gate (existing) | `make gate-test` (offline eval-gate fixture) |
| Markers available | `slow`, `eval` (`--run-eval`), `integration` (use for the nightly NSE test) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FCAST-02 | every feature `available_at <= T0` | unit | `pytest tests/unit/test_features_available_at.py -x` | ❌ Wave 0 |
| FCAST-02/P4 | walk-forward train set ⊂ {listing_date < T0_i}; R²>0.5 alarm fires | unit | `pytest tests/unit/test_walkforward_no_lookahead.py -x` | ❌ Wave 0 |
| FCAST-01/03 | CQR produces adaptive-width 80% interval on a fixture panel (offline, tiny) | unit | `pytest tests/unit/test_cqr_interval.py -x` | ❌ Wave 0 |
| FCAST-04 | global coverage/MAE/per-year-RMSE computed correctly from OOS rows | unit | `pytest tests/unit/test_forecast_metrics.py -x` | ❌ Wave 0 |
| FCAST-05/P9 | 4 baselines scored as-of-T0; DM test + release-gate logic | unit | `pytest tests/unit/test_baselines_dm.py -x` | ❌ Wave 0 |
| GMP-02/FCAST-02 | render imports no model module; predictor imports no GMP | unit (isolation) | `pytest tests/unit/test_forecast_isolation.py -x` | ❌ Wave 0 (mirror `test_gmp_isolation.py`) |
| FCAST-01 | forecast record round-trip + abstain/missing states | unit | `pytest tests/unit/test_forecast_schema.py -x` | ❌ Wave 0 |
| FCAST-03 | survivorship: built panel has non-zero withdrawn/delisted; MAAR in band | unit (offline sample) + integration (nightly live) | `pytest tests/unit/test_historical_panel.py`; `pytest -m integration` | ⚠ partial (`test_historical_panel.py` exists; extend) |
| UI-03 | forecast block renders band from a fixture record; empty/abstain/error states | unit (render) | `pytest tests/unit/test_forecast_block_render.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/unit -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests -q`
- **Phase gate:** full suite green + the offline gate + (checkpoint) one live universe build with non-zero withdrawn rows before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/unit/test_features_available_at.py` — FCAST-02 leakage gate
- [ ] `tests/unit/test_walkforward_no_lookahead.py` — P4 (train ⊂ pre-T0; R²>0.5 alarm)
- [ ] `tests/unit/test_cqr_interval.py` — FCAST-01/03 (adaptive-width interval on a fixture)
- [ ] `tests/unit/test_forecast_metrics.py` — FCAST-04 (coverage/MAE/per-year RMSE)
- [ ] `tests/unit/test_baselines_dm.py` — P9 (baselines as-of-T0 + DM gate)
- [ ] `tests/unit/test_forecast_isolation.py` — mirror `test_gmp_isolation.py` (reverse audit)
- [ ] `tests/unit/test_forecast_schema.py` — record round-trip + abstain/missing states
- [ ] `tests/unit/test_forecast_block_render.py` — UI states from a fixture record
- [ ] Extend `tests/unit/test_historical_panel.py` — assert withdrawn/delisted present after the two-source merge (monkeypatched fetchers)
- [ ] Add an `@pytest.mark.integration` nightly test hitting live NSE `public-past-issues` (CLAUDE.md requirement)
- [ ] Framework install: add xgboost/mapie/scikit-learn/mlflow/matplotlib/shap to `pyproject.toml`; `uv pip install` into `.venv`

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high` in config.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (public portfolio app) |
| V3 Session Management | no | Cache-only render; no sessions hold Phase-5 state |
| V4 Access Control | yes (light) | `is_known_drhp_id` allow-list gate before any `data/forecasts/` path is formed (path-traversal) — reuse the Phase 3 `_redflag_path` pattern |
| V5 Input Validation | **yes** | Untrusted scraped HTML/JSON coerced through the typed helpers (`coerce_price`/`coerce_date`/`normalize_status`); `drhp_id` from `st.query_params` allow-listed; invalid status RAISES (never coerced to a survivor) |
| V6 Cryptography | no | No secrets/crypto in Phase 5 (keyless public sources) |
| V10 SSRF / outbound | **yes** | `sources.ALLOWED_HOSTS` hard-coded allow-list; **extend to add `www.nseindia.com`** (+ confirm SEBI host); no URL derived from user/DRHP input (`_check_host` refuses) |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `drhp_id` in cache read | Tampering | `is_known_drhp_id` allow-list before path formation (existing pattern) |
| SSRF via a fetch host | Information disclosure | `ALLOWED_HOSTS` + `_check_host` (existing); extend allow-list, never build a URL from input |
| Malicious/malformed scraped payload → crash or fabricated row | Tampering/DoS | typed coercion → `None`→NaN retained; per-row isolation; per-source failure isolation (existing) |
| Supply-chain (new `nse`/`dieboldmariano` packages) | Tampering | `checkpoint:human-verify` before install (slopcheck unavailable); prefer inline DM; pin versions |
| GMP leaking into the model | (invariant breach) | `inspect.getsource` isolation tests both directions (§Isolation) |

## Sources

### Primary (HIGH confidence)
- [MAPIE `ConformalizedQuantileRegressor` docs](https://mapie.readthedocs.io/en/stable/generated/mapie.regression.ConformalizedQuantileRegressor.html) — constructor, fit/conformalize/predict_interval, prefit list order, quantile levels for `confidence_level=0.8`
- [MAPIE v1 release notes](https://mapie.readthedocs.io/en/stable/v1_release_notes.html) — 0.x→1.x API migration (`MapieQuantileRegressor`→`ConformalizedQuantileRegressor`, `alpha`→`confidence_level`, split fit/conformalize/predict_interval)
- [XGBoost Quantile Regression docs](https://xgboost.readthedocs.io/en/stable/python/examples/quantile_regression.html) — `reg:quantileerror` + `quantile_alpha`
- PyPI version checks (2026-07-15): mapie 1.4.1, xgboost 3.2.0, scikit-learn 1.9.0, mlflow 3.14.0, statsmodels 0.14.6, shap 0.51.0, matplotlib 3.11.0, nse 3.1.2, dieboldmariano 1.1.0
- Repo files read: `pipelines/historical/{__init__,sources,build,validate}.py`, `pipelines/{snapshot,redflag}.py`, `pages/02_snapshot.py`, `tests/unit/test_gmp_isolation.py`, `data/historical/README.md`, `CLAUDE.md`, `05-CONTEXT.md`, `05-UI-SPEC.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`

### Secondary (MEDIUM confidence)
- [BennyThadikaran/NseIndiaApi](https://github.com/BennyThadikaran/NseIndiaApi) — `listPastIPO`/`listCurrentIPO`/`listUpcomingIPO` → `/api/public-past-issues`, `/api/all-upcoming-issues?category=ipo`, `/api/ipo-current-issue`; cookie priming
- [SEBI Filings — Public Issues](https://www.sebi.gov.in/filings/public-issues.html) — issuer-side DRHP filings incl. withdrawn (P3 overlay)
- [chittorgarh withdrawn offer-document report (id 202)](https://www.chittorgarh.com/report/ipo-drhp-offer-document-withdrawn/202/) — withdrawn/cancelled list (coverage may be 2025+)
- [MAPIE metrics (coverage/width)](https://deepwiki.com/scikit-learn-contrib/MAPIE/4.1-metrics-and-evaluation) — `regression_coverage_score` / `regression_mean_width_score` (import path to confirm in 1.4.1)

### Tertiary (LOW confidence — needs live verification)
- chittorgarh `webnodejs …/data-read/83/…` JSON API — endpoint live, exact param order unverified (enrichment only)
- Exact field names in the NSE `public-past-issues` payload — confirm on first live pull, save raw JSON

## Metadata

**Confidence breakdown:**
- Standard stack (MAPIE CQR + XGBoost quantile): **HIGH** — official 1.x/2.0 docs + versions verified on PyPI
- Walk-forward wiring (displayed band = backtested band): **HIGH** — standard split-CQR-in-walk-forward; reasoning-derived but well-established, matches D5-11 exactly
- Diagnostics (coverage/MAE/RMSE, DM, calibration): **MEDIUM-HIGH** — metrics trivial; DM operationalization + PIT have documented caveats (A7/A8)
- Data sources (survivorship-safe universe): **MEDIUM** — endpoints identified + `nse` maintained, but NSE bot-detection, pre-2025 withdrawn coverage, and chittorgarh JSON params are live-fragile (A1–A4). This is the blocker.
- Isolation + record schema + reuse patterns: **HIGH** — direct mirrors of existing, tested code

**Research date:** 2026-07-15
**Valid until:** ~2026-08-15 for the modeling API (stable); ~2026-07-22 for the NSE/SEBI/chittorgarh endpoints (fast-moving, verify at Slice-1 start)
