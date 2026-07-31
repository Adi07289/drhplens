# Phase 5: Calibrated Listing-Day Forecaster - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-15
**Phase:** 5-Calibrated Listing-Day Forecaster
**Areas discussed:** Prediction horizon & cutoff, Training universe: source & scope, Feature philosophy, Abstention & small-N honesty, Honest forecast for already-listed IPOs

> Session started in the wrong working directory (`/Users/adityasharma` home instead of the
> `agentic-rag-app` project); resolved by targeting the project explicitly. User confirmed
> discussing Phase 5 now, ahead of the incomplete Phase 4 dependency.

---

## Prediction horizon & cutoff

### Feature-availability cutoff
| Option | Description | Selected |
|--------|-------------|----------|
| T0 — issue-open ("pre-apply") | Only info known at issue open; excludes subscription demand + GMP; low R² expected/honest; matches ROADMAP SC-5 | ✓ |
| T−1 of listing day | Stands day before listing (REQUIREMENTS FCAST-02 literal); subscription available but user can't act | |
| Both: pre-apply prod + T−1 research variant | Ship T0; keep T−1 in model card | |

**User's choice:** T0 — issue-open ("pre-apply").
**Notes:** Resolves the ROADMAP↔REQUIREMENTS conflict toward ROADMAP SC-5. FCAST-02's "T−1" wording is superseded.

### Target variable
| Option | Description | Selected |
|--------|-------------|----------|
| Raw listing-day return % | (close−issue)/issue; matches dataset + UI axis; market as features | ✓ |
| Market-adjusted return (MAAR) | Isolates IPO-specific abnormal return; must add drift back for UI | |

**User's choice:** Raw listing-day return %.

### Interval production method
| Option | Description | Selected |
|--------|-------------|----------|
| CQR — adaptive width | XGBoost reg:quantileerror ~0.1/0.9 + MAPIE conformal → per-IPO width | ✓ |
| Split-conformal, ~constant width | Point regressor + marginal calibration → uniform width | |

**User's choice:** CQR — adaptive width.

---

## Training universe: source & scope

### Universe source (chittorgarh HTML scraper dead)
| Option | Description | Selected |
|--------|-------------|----------|
| Chittorgarh JSON API | Reverse-engineer webnodejs data-read/83 endpoint; richest but fragile | |
| Official NSE/BSE + SEBI archive | Durable/authoritative; SEBI filings cover withdrawn issues | ✓ |
| Hybrid: NSE/BSE+SEBI base, chittorgarh enrich | Most robust, most build effort | |

**User's choice:** Official NSE/BSE + SEBI archive.
**Notes:** Seed universe from SEBI issue/withdrawal filings to preserve survivorship (P3); retire the stale `soup.find("table")` scraper. Chittorgarh JSON demoted to optional enrichment.

### Data scope before modeling
| Option | Description | Selected |
|--------|-------------|----------|
| Verified subset first, then expand | Clean ~200–300 slice → full pipeline → expand N | ✓ |
| Full 2014–present ~800–1000 up front | Max folds; stays fully blocked on fragile source | |
| Narrower clean window (2018–present) | Better coverage, fewer folds/sectors | |

**User's choice:** Verified subset first, then expand.

---

## Feature philosophy

### Feature families in candidate pool (multi-select)
| Option | Description | Selected |
|--------|-------------|----------|
| Issue structure | Size, price-band width, OFS/fresh, dilution, lot | ✓ |
| Market regime (P6) | NIFTY momentum, VIX, pipeline density, trailing listing-gain | ✓ |
| DRHP-derived signals | Phase 2 financials + Phase 3 NLP extraction | ✓ |
| Anchor-investor demand | Anchor book/quality/lock-in — T0-legal demand proxy | ✓ |

**User's choice:** All four families.

### Feature-set sizing vs ~200–300 N
| Option | Description | Selected |
|--------|-------------|----------|
| Lean & interpretable | ~8–15 features, SHAP-interpretable, low overfit | ✓ |
| Maximal / kitchen-sink | Many features + regularization; overfit risk | |

**User's choice:** Lean & interpretable.
**Notes:** Wide candidate pool, disciplined final selection; anchor features leakage-audited.

---

## Abstention & small-N honesty

### Abstention trigger
| Option | Description | Selected |
|--------|-------------|----------|
| Extrapolation + width guard | Abstain outside training support OR when interval uselessly wide | ✓ |
| Min-comparables threshold | Abstain if < N comparables by sector/size | |
| Rarely abstain — prefer wide band | Reserve abstention for hard failures | |

**User's choice:** Extrapolation + interval-width guard.

### Small-N sectors (P7)
| Option | Description | Selected |
|--------|-------------|----------|
| Pool small sectors into 'Other' | Sectors <30 pooled; report N-per-sector | ✓ |
| Hierarchical / partial pooling | Shrink toward global mean; doesn't fit XGBoost natively | |
| Drop sector as a feature | Report per-sector RMSE only | |

**User's choice:** Pool small sectors into 'Other'.

---

## Honest forecast for already-listed IPOs

### Leakage-avoidance for covered IPOs in the training window
| Option | Description | Selected |
|--------|-------------|----------|
| Walk-forward as-of-T0 prediction | Model trained only on IPOs listed before this one; displayed = backtested band | ✓ |
| Leave-one-out / K-fold | Uses future IPOs → lookahead (contradicts P4) | |
| Exclude covered IPOs from training | Wastes data; two model regimes | |

**User's choice:** Walk-forward as-of-T0 prediction.

### "How this was tested" metrics per page
| Option | Description | Selected |
|--------|-------------|----------|
| Global backtest metrics | Overall walk-forward numbers, identical per page; per-year RMSE is the time-slice | ✓ |
| Conditioned / sliced per IPO | Sector/size-cohort metrics; noisy at small N | |

**User's choice:** Global backtest metrics.

---

## Claude's Discretion

- Exact SEBI/NSE/BSE endpoints + scraping/caching mechanics; nightly integration test.
- XGBoost hyperparameters, quantile levels, MAPIE conformal variant, calibration/PIT plots.
- `data/forecasts/<drhp_id>.json` schema (cache-only; render imports no model module).
- Exact sector taxonomy + precise small-N pooling threshold (~30 guideline).
- Diebold–Mariano wiring vs four baselines; R²>0.5 leakage red-flag check.
- Empirical tuning of abstention support/width thresholds.

## Deferred Ideas

- T−1-of-listing model variant (optional model-card sensitivity analysis).
- Retrospective forecast-vs-actual calibration page (TODOS E7 / Phase 6).
- Chittorgarh JSON API as optional enrichment source.
- Hierarchical/partial-pooling sector model.
- MAAR target.
- Full 2014-present universe up front.
