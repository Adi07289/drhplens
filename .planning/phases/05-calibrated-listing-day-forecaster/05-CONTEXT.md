# Phase 5: Calibrated Listing-Day Forecaster - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 ships a **calibrated 80% listing-day-return prediction interval** for each
covered IPO, backed by an XGBoost + MAPIE conformal regressor that is walk-forward
backtested against a historical Indian mainboard-IPO universe, with a committed
public **model card** and a **GMP-vs-model gap** signal.

**The UI is a CLOSED contract** — `05-UI-SPEC.md` locks all four visual decisions
(interval band as the dominant visual, faint median tick with no point-estimate
headline, muted GMP marker, always-visible "How this was tested" strip, model card
on `/methodology`). This discussion clarifies **how to build the model**, not how it
looks.

**In scope:** the forecaster (features → walk-forward CV → CQR/MAPIE conformal
intervals → model card), the historical universe build that trains it, the
per-IPO forecast records the UI reads, the GMP-vs-model gap (display-layer), and
the `/methodology` model-card section content.

**Out of scope (later phases / v2):** RAGAS/DeepEval eval dashboards + inline RAG
metric surfacing (Phase 6); agentic LangGraph upgrade (Phase 6); retrospective
forecast-vs-actual calibration page (TODOS E7 / Phase 6); multi-IPO side-by-side
compare (v2).

</domain>

<decisions>
## Implementation Decisions

### Prediction horizon, target & interval
- **D5-01 — Cutoff = T0 issue-open ("pre-apply").** Features must be
  `available_at <= T0` (the issue-open day). This **resolves the ROADMAP↔REQUIREMENTS
  conflict**: ROADMAP SC-5 (`available_at <= T0`, "pre_apply", subscription multiples
  excluded) is canonical; REQUIREMENTS FCAST-02's literal "T−1 of listing day" wording
  is **superseded** — the planner should treat T0 issue-open as the cutoff and note the
  reconciliation. Rationale: a pre-apply forecast is the only *actionable* one (the user
  can still apply), the model sees **no subscription demand and no GMP**, and the
  resulting **low R² is the honest result** — the roadmap's own P4 guard treats R²>0.5
  as a leakage red flag.
- **D5-02 — Target = raw listing-day return %** = `(listing_day_close − issue_price) /
  issue_price`. Exactly the dataset's `listing_day_return` column and the UI's
  "listing-day return %" axis. Market conditions enter as **features** (D5-06b), NOT by
  adjusting the target — **MAAR (market-adjusted) target was considered and rejected**
  (would force adding market drift back for the UI number and complicate the honesty story).
- **D5-03 — Interval = CQR (Conformalized Quantile Regression), adaptive width.**
  XGBoost quantile regressors (`reg:quantileerror` at ~0.1/0.9) wrapped in MAPIE
  conformal calibration → the 80% interval **width varies per IPO** (wide for genuinely
  uncertain issues, tight for predictable ones). Makes "uncertainty is the message"
  literally true per-IPO. Split-conformal constant-width was considered and rejected
  (undersells the heteroscedasticity that is the whole point). 80% coverage target is
  locked by ROADMAP.

### Training universe: source & scope
- **D5-04 — Universe source pivots to official NSE/BSE + SEBI archive.** The existing
  chittorgarh HTML scraper is **dead** (`fetch_chittorgarh_index` uses
  `soup.find("table")`; chittorgarh migrated to a Next.js app → 0 rows). Retire it as
  the primary path. **Seed the universe from SEBI issue/withdrawal filings** so
  withdrawn/pulled/delisted IPOs survive (P3 survivorship control — a 2014-present
  universe with zero withdrawn/delisted rows is a survivorship red flag). Exchange
  "listed" feeds skew survivor-only and must NOT be the sole source. The chittorgarh
  JSON API (`webnodejs.chittorgarh.com/cloud/report/data-read/83/…`, per-FY) is demoted
  to an **optional enrichment/cross-check**, not primary.
- **D5-05 — Verified subset first, then expand.** Build a clean **~200–300-IPO verified
  slice** first, exercise the **full pipeline end-to-end** (feature build → walk-forward
  CV → CQR/MAPIE conformal → model card), THEN expand N toward the full 2014-present
  universe. De-risks the data blocker and protects the ≥35% non-LLM modeling budget
  (P11 — cut agent scope before modeling scope). Full-universe-up-front was rejected
  (stays fully blocked on a fragile source).

### Feature philosophy
- **D5-06 — Candidate pool spans all four families** (final set is curated lean, D5-07):
  - **(a) Issue structure** — issue size (₹ raised), price-band width %, OFS-vs-fresh
    split, promoter dilution %, lot size / min investment.
  - **(b) Market regime (P6)** — NIFTY 3M/6M momentum, India VIX level, IPO pipeline
    density, trailing-N listing-gain average. Turns regime-shift-blindness into signal.
  - **(c) DRHP-derived signals** — reuse Phase 2 financials (revenue growth, margins,
    RoE, debt) + Phase 3 NLP extraction (red-flag count, RPT intensity, use-of-proceeds
    mix, promoter holding). This is the "NLP extraction fused INTO the model" narrative.
  - **(d) Anchor-investor demand** — anchor book / investor quality / lock-in. The ONE
    demand-ish signal legitimately available at T0 (anchor allocation is disclosed the
    day before issue open).
- **D5-07 — Final feature set is LEAN & interpretable (~8–15 features).** Wide candidate
  pool, disciplined final selection via EDA + importance/stability under walk-forward.
  SHAP/importance-interpretable for the model card. Matches expected-low-R² honesty and
  small-N reality (P4/P7). Kitchen-sink was rejected (overfit risk on ~200–300 rows).
- **D5-08 — Every feature carries a verified `available_at <= T0` timestamp (FCAST-02),
  and anchor-investor features carry an EXPLICIT leakage audit.** Anchor features are
  borderline — they must read the **pre-open anchor allocation only**, never post-open
  subscription. GMP and final subscription multiples remain excluded. The leakage audit
  is documented in the model card.

### Abstention & small-N honesty
- **D5-09 — Abstention trigger = extrapolation + interval-width guard (conformal-native).**
  The model abstains (renders the UI's locked "not enough comparable history" note, no
  band) when the IPO's features fall **outside the training support** OR the calibrated
  interval is **so wide it conveys nothing useful**. Abstention is a property of the
  calibration, not an arbitrary rule. A bare min-comparables count was considered but
  folded into "support" reasoning.
- **D5-10 — Small-N sectors (P7): pool sectors below ~30 IPOs into a pooled 'Other'
  bucket**, and **report N-per-sector** so the thinness is visible. Hierarchical /
  partial-pooling was considered and deferred (doesn't fit XGBoost natively; marginal
  gain at this N). Dropping sector entirely was rejected (discards real signal).

### Honest forecast for already-listed covered IPOs
- **D5-11 — Displayed per-IPO forecast = walk-forward as-of-T0 out-of-sample
  prediction.** The band shown for any covered IPO is produced by the model state
  trained **only on IPOs that listed before that IPO's T0**. So the **displayed band =
  the backtested band** — it is the same out-of-sample prediction the walk-forward
  backtest scores. Honors P4 (no lookahead) and needs no extra machinery. Leave-one-out
  (uses future data → lookahead) and exclude-covered-IPOs-from-training (wastes data,
  two model regimes) were both rejected.
- **D5-12 — "How this was tested" metrics are GLOBAL walk-forward numbers**, identical
  on every IPO page (coverage, MAE, per-year RMSE; per-year RMSE is the one time-slice).
  Matches FCAST-04 and the UI-SPEC strip as written, and is statistically stable.
  Per-sector-conditioned metrics were considered and rejected (small-N noise, P7;
  diverges from the UI-SPEC's global framing).

### Locked upstream (carried forward — NOT re-decided here)
- **UI fully locked by `05-UI-SPEC.md`** (L5-1…L5-4 + inherited honesty invariant: no
  green/red, no badges, no point-estimate headline, band width is the dominant signal).
- **Model family + eval gates locked by ROADMAP:** XGBoost + MAPIE; four baselines
  (predict-zero, global-median, trailing-12-IPO-median, sector-mean) + Diebold–Mariano
  significance test as the **release gate** (P9); walk-forward only (P4); honest
  empirical coverage even if it misses 80% (P17).
- **GMP isolation is a hard invariant** (D4-03 / GMP-02 / FCAST-02): the model imports
  no GMP; the GMP-implied-return marker is a **display-layer** read of cached GMP +
  cached issue price only, and the forecast render imports no model/training module
  (pin with an `inspect.getsource` no-model-import audit, mirroring the Phase 4 GMP test).

### Claude's Discretion (research / planner territory)
- Exact SEBI / NSE / BSE endpoints + scraping/caching mechanics for the universe build;
  add a nightly integration test (per CLAUDE.md India-data guidance).
- XGBoost hyperparameters, exact quantile levels, MAPIE conformal variant (CQR split vs
  CV+/Jackknife+), calibration + PIT-histogram plotting.
- The `data/forecasts/<drhp_id>.json` forecast-record schema (interval bounds, median,
  global coverage/MAE/per-year-RMSE, abstain flag, and an as-of/out-of-sample provenance
  marker + model version) — **must be cache-only; the UI render imports no model module**.
- Exact sector taxonomy and the precise small-N pooling threshold (guideline ~30).
- Diebold–Mariano test wiring against the four baselines; the R²>0.5 leakage red-flag check.
- Empirical tuning of the abstention support/width thresholds (D5-09).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 5: Calibrated Listing-Day Forecaster" — goal, 5 success
  criteria, requirements (FCAST-01..05, GMP-03, UI-03), pitfalls owned (P4, P6, P7, P9,
  P11, P17, P21), and the "~1 EDA week" research flag. **Note SC-5 (`available_at <= T0`)
  governs the cutoff — see D5-01.**
- `.planning/REQUIREMENTS.md` — full text of FCAST-01..05, GMP-03, UI-03. **FCAST-02's
  "T−1 of listing" wording is superseded by D5-01 (T0 issue-open); reconcile when planning.**
- `.planning/phases/05-calibrated-listing-day-forecaster/05-UI-SPEC.md` — **LOCKED UI
  design contract** (L5-1…L5-4, states/copy, GMP-implied-return conversion, forecast-block
  insertion point in `pages/02_snapshot.py`, `data/forecasts/<drhp_id>.json` recommendation,
  no-model-import isolation). MUST read before touching any UI.

### Stack & India-specific data
- `CLAUDE.md` (repo root) — locked stack: XGBoost 2.x (`reg:quantileerror`), MAPIE 1.x,
  scikit-learn, MLflow (local), pandas/numpy; §"India-Specific Data-Source Notes" (NSE/BSE/
  SEBI/chittorgarh/yfinance caveats); §"What NOT to Use" (forecasting without time-based
  splits; nsepy is dead); §"Deployment Plan" (free-tier, HF Spaces, commit `mlruns/`).

### Historical dataset (the training foundation) — CURRENTLY BLOCKED
- `data/historical/README.md` — column contract, the **BLOCKED chittorgarh build**
  (source rot 2026-07-07), and the documented fix path (D5-04 pivots to NSE/BSE + SEBI).
- `pipelines/historical/__init__.py` — `PANEL_COLUMNS`, `STATUS_VALUES` (P3 taxonomy),
  `compute_listing_day_return()` (the honest NaN-preserving target formula), `assemble_panel()`.
- `pipelines/historical/build.py` / `sources.py` / `validate.py` — the universe assembler
  (`fetch_chittorgarh_index` is the stale selector to replace), MAAR ~7% sanity-check.
- `data/historical/ipo_panel.csv` / `.parquet` — the 7-row **fictional-issuer sample**
  (schema only; NOT real data — the real build is D5-04/D5-05).

### Carried-forward decisions & isolation patterns
- `.planning/phases/04-historical-ipo-dataset-peer-comparator-gmp-display/04-CONTEXT.md`
  — D4-03 (GMP isolation invariant Phase 5 must pin), dataset-internals deferral (return
  target, status taxonomy) now realized here, cache-first pattern.
- `.planning/phases/03-structured-signal-extraction-red-flag-table/03-CONTEXT.md` —
  per-field confidence + "not disclosed" honesty pattern (mirrored by D5-09 abstention);
  Phase 3 NLP extraction outputs feed D5-06c features.
- `tests/unit/test_gmp_isolation.py` — the existing GMP no-import audit to MIRROR for the
  forecast render's no-model-import gate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipelines/historical/` — the panel schema + validator + CLI already exist; Phase 5
  replaces the dead universe source (D5-04), adds feature engineering (kept out of the
  Phase 4 schema deliberately), and consumes `compute_listing_day_return()` as the target.
- `pipelines/snapshot.py`, `pipelines/redflag.py` — the **precompute → write
  `data/<kind>/<drhp_id>.json` → `load_*()`** cache pattern to MIRROR for
  `data/forecasts/<drhp_id>.json`.
- `data/catalogue_loader.py` (`is_known_drhp_id()`) — allow-list guard the forecast read
  must reuse before any cache read.
- `pages/02_snapshot.py` — forecast block inserts after `_render_peer_block(...)` and
  before the ranked-risks branch (UI-SPEC L5-4); same guarded try/except posture.
- `pages/01_methodology.py` — gains the forecaster model-card section (calibration plot,
  PIT histogram, four baselines + DM test, `available_at` leakage audit, limitations).
- `ui/copy.py` + `compliance.scrubber` — all new forecast copy lands here under the
  import-time banned-token assertion (`target` is a banned stem — use "range"/"interval").
- `app/static/drhplens.css` — the single CSS source; new `.drhp-forecast-*` classes (per UI-SPEC).
- Phase 2 financials + Phase 3 extraction outputs — feature sources for D5-06c.

### Established Patterns
- `drhp_id` FK threads every surface; **cache-first render** (no live model/scrape call
  at page render — the forecast is precomputed offline and committed).
- Honesty-first invariant (no red/green, no badges, no verdict) is load-bearing app-wide.
- Module-boundary isolation (GMP) enforced by an import-audit unit test — replicate for
  the forecast render (no model/training import).

### Integration Points
- New `data/forecasts/` cached-record kind mirrors `data/snapshots/` / `data/redflag/` /
  `data/gmp/`.
- The forecaster (offline: MLflow-tracked training + walk-forward backtest) produces both
  the committed model card and the per-IPO forecast records the Streamlit page reads.
- The GMP-implied-return marker reads the SAME cached `data/gmp/<drhp_id>.json` the quiet
  GMP block reads (one cache, one caveat posture) — display layer only.

</code_context>

<specifics>
## Specific Ideas

- **"Displayed band = backtested band"** is the honesty keystone (D5-11): the number a
  user sees on an already-listed IPO is literally a number the model earned out-of-sample
  under walk-forward — no in-sample flattery.
- **Anchor-investor demand is the single legitimate T0 demand proxy** (D5-06d) — a
  sophisticated, defensible feature that distinguishes this from a naive issue-structure model.
- **Adaptive-width CQR (D5-03)** so the interval itself communicates per-IPO uncertainty —
  the model's honesty is visible in the geometry the UI already renders as "the message."
- Low R² is a **feature, not a bug** — the model card should state plainly that a pre-apply
  forecast with no demand signal is expected to be humble, and that the P4 guard would flag
  a suspiciously high R² as leakage.

</specifics>

<deferred>
## Deferred Ideas

- **T−1-of-listing model variant** — rejected as the production model (D5-01); could
  optionally appear in the model card as a *sensitivity analysis* quantifying how much the
  subscription-window information is worth. Optional, not required.
- **Retrospective forecast-vs-actual calibration page** (TODOS.md E7) — "we predicted
  [range] at T-1; actual was [X]" with a calibration delta. Future phase (Phase 6 eval /
  v2). Strong model-card material once covered IPOs list.
- **Chittorgarh JSON API reverse-engineering** — demoted to optional enrichment/cross-check
  (D5-04), not the primary source. Revisit only if NSE/BSE + SEBI coverage has gaps.
- **Hierarchical / partial-pooling sector model** — considered for P7, deferred (D5-10);
  pooling into 'Other' is the default.
- **MAAR (market-adjusted) target** — considered, rejected (D5-02); raw return chosen.
- **Full 2014-present universe up front** — deferred behind verified-subset-first (D5-05).

### Reviewed Todos (not folded)
- **E7 (retrospective forecast-vs-actual page)** — reviewed; belongs in Phase 6 / v2, not
  folded into Phase 5 scope.

</deferred>

---

*Phase: 5-Calibrated Listing-Day Forecaster*
*Context gathered: 2026-07-15*
