# Roadmap: DRHPLens

**Created:** 2026-05-28
**Mode:** MVP (vertical-slice progression)
**Granularity:** standard
**Coverage:** 42/42 v1 requirements mapped
**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved.

## Phases

- [ ] **Phase 1: Foundation + MVP-A (Cited Q&A on One IPO)** - End-to-end cited Q&A working on one hand-loaded DRHP with full compliance posture, citation infrastructure, and deployed demo URL.
- [ ] **Phase 2: Multi-IPO Catalogue + DRHP Snapshot Surface** - Browseable catalogue of 5-10 IPOs, each with a per-IPO snapshot page (metadata, business summary, financials, risks, use of proceeds, promoter section), all DRHP-cited.
- [ ] **Phase 3: Structured Signal Extraction (Red-Flag Table)** - NLP-extracted structured red-flag table per IPO with per-field confidence scores, hand-labeled gold set evaluation (F1), and numeric-faithfulness release gate.
- [ ] **Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display** - Survivorship-corrected historical IPO dataset (SEBI-sourced universe with status column), peer multiples comparison table, GMP read-only display, Indian-context formatting throughout.
- [ ] **Phase 5: Calibrated Listing-Day Forecaster** - XGBoost + MAPIE conformal regression with walk-forward backtest, four baselines, committed model card, GMP-vs-model gap signal, uncertainty rendered as first-class UI.
- [ ] **Phase 6: Full Eval Harness + Agentic Polish + Portfolio Surface** - RAGAS/DeepEval/Langfuse eval dashboards, in-UI metric surfacing, "Show your work" pane, agent trace visibility, portfolio-presentable repo (README + methodology + failure gallery).

## Phase Details

### Phase 1: Foundation + MVP-A (Cited Q&A on One IPO)
**Goal:** A retail user can pick one hand-loaded Indian mainboard IPO, ask a plain-English question about its DRHP, and receive a grounded answer with clickable span-level citations on a mobile-responsive web page that frames everything as informational/educational only.
**Mode:** mvp
**Depends on:** Nothing (foundation phase)
**Requirements:** INGEST-01, INGEST-02, INGEST-03, RAG-01, RAG-02, RAG-03, TRUST-01, TRUST-02, TRUST-03, TRUST-04, UI-01, UI-02, OPS-02
**Success Criteria** (what must be TRUE):
  1. User can visit a public URL (HF Spaces or equivalent free-tier host) on a phone and see a working chat interface (OPS-02, UI-01).
  2. User asks a plain-English question about the single loaded DRHP and receives a grounded answer in which every claim renders as a clickable superscript citation chip that expands to show the source span and links to the DRHP page (RAG-01, RAG-02, UI-02).
  3. When the user asks a question the DRHP does not address, the system refuses with "This DRHP does not address X" rather than fabricating an answer (RAG-03, TRUST-04).
  4. A persistent disclaimer + first-use modal + per-answer footer frame the product as informational/educational, and the output never contains banned prescriptive tokens (buy, sell, subscribe, avoid, recommend, target, fair value) (TRUST-01, TRUST-02, TRUST-03).
  5. The system ingests, parses, and indexes the one DRHP PDF (300-500 pages) with section-aware chunking and page-anchored metadata, so every retrieved chunk carries (drhp_id, section, page) for the cite-check node to verify against (INGEST-01, INGEST-02, INGEST-03, TRUST-04).
  6. **`/methodology` stub link rendered on the home page** (placeholder content until Phase 6's LAND-01 replaces it with the full recruiter landing page) — prevents resume deep-links 404ing between Phase 1 and Phase 6.
**Plans**: TBD
**UI hint**: yes

**Pitfalls owned:** P1 (SEBI boundary — disclaimer infrastructure + banned-token scrubber must land here), P5 (citation drift — span-level citations from day one), P19 (demo-day fragility — pre-index corpus, cache, warm-keep), P20 (scope creep — do not proceed until MVP-A is deployed and demoable).

---

### Phase 2: Multi-IPO Catalogue + DRHP Snapshot Surface
**Goal:** A retail user can browse a catalogue of 5-10 recent Indian mainboard IPOs (plus 1-2 currently-open), pick any IPO, and see a per-IPO snapshot page that surfaces the core DRHP signals — metadata, plain-English business summary, key financials, prioritized risks, use of proceeds, promoter section — each field citing its DRHP source.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** SNAP-01, SNAP-02, SNAP-03, SNAP-04, SNAP-05, SNAP-06, SNAP-07, OPS-01
**Success Criteria** (what must be TRUE):
  1. User can browse a list of 5-10 recent mainboard IPOs + 1-2 currently-open IPOs and select any one to view its snapshot page (SNAP-01, OPS-01).
  2. User sees a per-IPO metadata header with price band, lot size, issue dates, issue size, fresh-issue vs OFS split, and lead managers — all extracted from the RHP cover page (SNAP-02).
  3. User reads a plain-English business-model summary, a key-financials snapshot (3-5 year revenue, profit, margins, debt, ROE, ROCE), a prioritized risk-factors summary, and a use-of-proceeds breakdown — each block citing the DRHP page it was sourced from (SNAP-03, SNAP-04, SNAP-05, SNAP-06).
  4. User sees a promoter/management section with names, pre/post holdings, pledging status, and prior matters, with citations to the DRHP promoter section (SNAP-07).
  5. The OFS-vs-fresh-issue split in use-of-proceeds is visually foregrounded (matches Indian retail's primary "promoter cash-out vs growth capital" mental model) (SNAP-06).
**Plans**: TBD
**UI hint**: yes

**Pitfalls owned:** P14 (brittle DRHP ingestion — multi-source redundancy + SHA versioning + DRHP-vs-RHP discrimination must be solid by end of phase), P13 (embedding mismatch on Indian-English — hybrid retrieval BM25+dense+rerank upgrades land here).

---

### Phase 3: Structured Signal Extraction (Red-Flag Table)
**Goal:** A retail user opening any covered IPO sees a structured red-flag signal table (RPT % of revenue, OFS vs fresh-issue %, promoter pledge %, customer concentration, auditor history, debt trajectory, going-concern mentions), each field with a visible extractor-confidence score, backed by a hand-labeled gold-set F1 evaluation committed in the repo and a numeric-faithfulness release gate of >=0.95.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** EXTRACT-01, EXTRACT-02, EXTRACT-03, EVAL-03, METHOD-01
**Success Criteria** (what must be TRUE):
  1. User sees a structured red-flag table on every IPO snapshot page containing RPT % of revenue, OFS vs fresh-issue %, promoter pledge %, customer concentration (if disclosed), auditor history, debt trajectory, and going-concern mentions (EXTRACT-01).
  2. Every extracted field renders alongside a confidence score the user can see (e.g., "high / medium / low" or a numeric badge), making extractor uncertainty visible rather than hidden (EXTRACT-02).
  3. A per-field F1 score from a hand-labeled gold set of 20-30 DRHPs is committed to the repo under `eval/gold/extraction_labels.jsonl` and surfaced on the methodology page (EXTRACT-03).
  4. A numeric-faithfulness eval track exists with >=0.95 release gate on a 50-query numeric-only eval set — the app refuses to deploy below this threshold (EVAL-03).
  5. Risk extraction outputs are bucketed into issuer-specific vs industry-standard risks (IDF-weighted), so the user sees the issuer-specific risks foregrounded — not boilerplate that appears in every IPO (P12 mitigation, reinforces EXTRACT-01).
  6. **"Show your work" methodology pane (METHOD-01, CEO-approved cherry-pick E1)**: a one-click expansion on any answer reveals retrieval query, retrieved chunks with scores, prompt used, sources cited, and faithfulness/citation eval scores — pulled forward from Phase 6 so DS rigor is visible from Phase 3's first demoable surface.
**Plans**: TBD
**UI hint**: yes

**Pitfalls owned:** P2 (hallucinated numbers — two-stage structured extraction protocol locked in here), P12 (risk-factor boilerplate inflating metrics — IDF weighting + issuer-specific/boilerplate split), P10 (evaluation theater — every extraction metric gets an interpretation paragraph + failure gallery).

---

### Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display
**Goal:** A retail user on an IPO page sees a live peer-multiples comparison table (P/E, P/B, EV/EBITDA, ROE) against the DRHP-disclosed listed peers, plus a clearly-caveated read-only GMP display from public aggregators — all rendered with correct Indian-context formatting (lakh/crore, INR symbols, RPT/QIB/NII/RII glossary tooltips). Behind the UI, a survivorship-corrected historical Indian mainboard IPO dataset (SEBI-issuer-side sourced, with explicit status column) is built and validated against the published ~7% median baseline.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** PEER-01, PEER-02, GMP-01, GMP-02, UI-04
**Success Criteria** (what must be TRUE):
  1. User sees the DRHP's own "Comparison with Listed Peers" peer set surfaced on the IPO page, anchored to the DRHP section it came from (PEER-01).
  2. User sees peer multiples (P/E, P/B, EV/EBITDA, ROE) sourced from screener.in / yfinance / NSE / BSE displayed in a table alongside the IPO's own DRHP-derived metrics (PEER-02).
  3. User sees a read-only GMP value scraped from public aggregators with an explicit, above-the-fold caveat about provenance and reliability — and the GMP value is computationally isolated from any model feature pipeline (GMP-01, GMP-02).
  4. All financial numbers render in Indian conventions (lakh/crore, INR symbols), and acronyms (RPT, QIB, NII, RII) carry hoverable glossary tooltips (UI-04).
  5. The historical IPO dataset (~800-1000 mainboard IPOs from 2014-present) is committed to the repo with an explicit `status` column (withdrawn / listed_alive / delisted / merged / name_changed), and the dataset's median listing-day return is sanity-checked against the published ~7% academic baseline — flagged in the methodology page if it materially diverges (foundation for Phase 5; not yet user-visible).
**Plans**: TBD
**UI hint**: yes

**Pitfalls owned:** P3 (survivorship bias — SEBI-issuer-side sourcing + status column + replace-with-NaN + ~7% median sanity check), P15 (yfinance data quality — NSE bhavcopy as primary, corporate-actions ledger), P16 (screener.in ToS / rate limits — aggressive caching, throttling, Plan-B source), P14 (brittle DRHP ingestion continues here for historical filings).

**Research flag:** Run a `jugaad-data` endpoint validation spike at phase start (~1 day) before committing to it as primary NSE source. Build a nightly integration test.

---

### Phase 5: Calibrated Listing-Day Forecaster
**Goal:** A retail user on an IPO page sees a calibrated listing-day return range (80% prediction interval) rendered as the *primary* visual element (not a point estimate), with the gap between the model forecast and the displayed GMP shown as a transparent comparative signal, backed by a walk-forward backtested XGBoost + MAPIE conformal regressor whose data, features, baselines, significance tests, calibration plots, and limitations are all committed as a public model card in the repo.
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** FCAST-01, FCAST-02, FCAST-03, FCAST-04, FCAST-05, GMP-03, UI-03
**Success Criteria** (what must be TRUE):
  1. User sees a calibrated listing-day return range with an 80% prediction interval rendered as the dominant visual on the forecast section (no green/red coding, no point-estimate-as-headline) — uncertainty is the primary signal (FCAST-01, UI-03).
  2. User sees the gap between the displayed GMP and the GMP-free model forecast called out explicitly as a comparative signal ("GMP says X; the GMP-free model says Y; here's the gap") (GMP-03).
  3. The forecast page surfaces empirical interval coverage, MAE, and per-year RMSE from the walk-forward backtest, visible to any user (FCAST-04).
  4. A model card is committed to the repo covering: training window, feature list with `available_at` timestamps, four baselines (predict-zero, global-median, trailing-12-IPO-median, sector-mean) with Diebold-Mariano significance test, calibration plots, PIT histogram, and known limitations (FCAST-03, FCAST-05).
  5. Every forecast feature has a verified `available_at <= T0` timestamp (issue-open day); GMP and final subscription multiples are explicitly excluded from the production `pre_apply` model — and a leakage audit is documented in the model card (FCAST-02).
**Plans**: TBD
**UI hint**: yes

**Pitfalls owned:** P4 (lookahead bias — feature `available_at` audit, walk-forward only, R^2 > 0.5 red-flag check), P6 (regime-shift blindness — NIFTY 6M / VIX / pipeline-density regime features, per-year RMSE), P7 (small-N sector slices — N-per-sector reported, sectors < 30 pooled or hierarchical), P9 (naive baselines beat the model — four baselines + significance test as release gate), P11 (all-LLM-glue — this phase is the >=35% non-LLM modeling budget; cut agent scope before cutting modeling scope), P17 (calibration theater — empirical coverage on held-out test, conformal not parametric), P21 (UX implies advice — interval as primary visual, no green/red coding).

**Research flag:** India-IPO feature engineering from public data has no open reference implementation. Plan ~1 EDA week in notebooks at phase start before committing to the feature set.

---

### Phase 6: Full Eval Harness + Agentic Polish + Portfolio Surface
**Goal:** A retail user (and a recruiter reviewing the portfolio) sees the DS rigor surface visibly: per-page RAG faithfulness / retrieval coverage / citation accuracy displayed inline, a "Show your work" pane expandable on any claim to reveal retrieval query + retrieved chunks + prompt + sources + eval scores, full agent traces captured via Langfuse, and a portfolio-presentable repo with README, methodology writeup, model card, failure gallery, and committed eval dashboards.
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** EVAL-01, EVAL-02, EVAL-04, EVAL-05, OPS-03, LAND-01, FAILGAL-01
**Success Criteria** (what must be TRUE):
  1. User sees per-IPO RAG faithfulness, retrieval recall@k, and citation accuracy scores surfaced inline on the IPO page (e.g., "This page's RAG faithfulness: 0.91") — computed by a committed RAGAS/DeepEval/custom-citation-metric eval suite (EVAL-01, EVAL-02).
  2. User can click "Show your work" on any claim or forecast to expand a pane revealing the retrieval query, retrieved chunks (with scores), prompt, sources used, and eval scores for that specific claim (EVAL-04).
  3. Every agent trace is captured via Langfuse (or equivalent), reviewable by the developer, with cost / latency / tool-call counts / failure-mode taxonomy surfaced on an operational dashboard (EVAL-05).
  4. The public repo contains a portfolio-presentable README (methodology-forward, paper-like), a model card for the forecaster, a failure gallery (>=10 inspected RAG / extraction / forecast failures with commentary), and committed HTML eval dashboards under `eval/reports/` per release (OPS-03).
  5. A SEBI legal-review checkpoint has been completed before this phase ships publicly (P1 final gate); the agent is upgraded to full multi-tool LangGraph orchestration with TTL + semantic call dedup + supervisor stress-tested against weird-user-query inputs (P8 mitigation).
  6. **Recruiter landing page (LAND-01, CEO-approved cherry-pick E2)**: `/methodology` deep-linkable page renders model card + methodology writeup + failure gallery link + per-IPO eval dashboard summary — the page resume deep-links land on; the Phase 1 stub link is replaced with this full implementation.
  7. **Live browseable failure gallery (FAILGAL-01, CEO-approved cherry-pick E6)**: `/failures` page renders the eval/failures gallery (≥10 documented failures across RAG / extraction / forecast surfaces) with category, query, expected vs actual, and post-mortem note — browseable and searchable, not just a markdown file in `eval/`.
**Plans**: TBD
**UI hint**: yes

**Pitfalls owned:** P8 (agent infinite loops — TTL + semantic dedup + supervisor stress-tested), P10 (evaluation theater — every headline metric gets interpretation paragraph + failure gallery + human spot-check of >=50 examples), P18 (agent answers without retrieving — retrieval-mandatory contract + output-schema enforcement + trace audit eval), P1 final gate (SEBI legal-review checkpoint before public launch), P19 (demo-day fragility — final pass: pre-index corpus, cache LLM responses, cron pinger, offline demo video).

**Research flag:** DeepEval CI integration and Langfuse custom-score callbacks may benefit from a brief exploration spike at phase start (~1-2 days).

---

## Progress Tracking

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + MVP-A | 0/0 | Not started | - |
| 2. Multi-IPO Catalogue + DRHP Snapshot | 0/0 | Not started | - |
| 3. Structured Signal Extraction | 0/0 | Not started | - |
| 4. Historical IPO Dataset + Peer Comparator + GMP | 0/0 | Not started | - |
| 5. Calibrated Listing-Day Forecaster | 0/0 | Not started | - |
| 6. Full Eval Harness + Agentic Polish + Portfolio | 0/0 | Not started | - |

## Cross-Cutting Invariants

These hold across every phase and are non-negotiable design constraints derived from PITFALLS.md:

- **Compliance posture is hardcoded, not decorative.** Disclaimer + banned-token scrubber + no-personalization + no-fees enforced at system-prompt and output-renderer level from Phase 1 onward (P1).
- **Citations are span-level, not page-level, from day one.** The LLM emits `claim_id` references; the renderer resolves citations from the retrieval object; a non-LLM cite-check node validates every claim against the retrieved evidence set before emit (P5).
- **Numeric-faithfulness >=0.95 is a release gate** on every release from Phase 3 onward. No shipping below threshold (P2, EVAL-03).
- **Historical IPO universe is survivorship-corrected** — sourced from SEBI offer-document filings (not exchange listing feeds), with explicit `status` column. Median listing-return must be sanity-checked against the published ~7% baseline (P3).
- **All forecast features carry an `available_at` timestamp.** Walk-forward CV only. No random k-fold across years. GMP and final subscription multiples are excluded from the production model (P4).
- **>=35-40% of total build time is on non-LLM modeling** (forecaster + structured extractors). Cut agent scope before cutting modeling scope (P11).
- **Naive baselines are reported alongside every model.** If the ML forecaster doesn't beat a trailing-12-IPO-median baseline with statistical significance, the portfolio piece says so honestly (P9).
- **GMP display !== GMP feature.** GMP is shown read-only with caveats; it never enters any model pipeline (GMP-01, GMP-02, P4).
- **Storage is the integration bus.** Batch pipelines write; on-demand tools read; no pipeline-to-pipeline direct calls; no batch pipeline calls the agent (architecture invariant).
- **Eval hooks are instrumented from Phase 1.** Dashboard polish is Phase 6, but every agent run writes a full trace from day one (P10).
- **Agent traces carry `claim_id` references from Phase 1 day one** (not bolted on later). Every generated claim is emitted with a `claim_id` referencing the retrieval object; the renderer resolves citations and the methodology pane (METHOD-01, Phase 3) consumes the same data structure. Necessary so Phase 3's "Show your work" pane has structured data to render — captured here so it isn't forgotten during Phase 1 plan-phase.

## Coverage

**v1 Requirements:** 45 total
**Mapped to phases:** 45
**Unmapped:** 0

| Requirement | Phase |
|-------------|-------|
| INGEST-01 | Phase 1 |
| INGEST-02 | Phase 1 |
| INGEST-03 | Phase 1 |
| SNAP-01 | Phase 2 |
| SNAP-02 | Phase 2 |
| SNAP-03 | Phase 2 |
| SNAP-04 | Phase 2 |
| SNAP-05 | Phase 2 |
| SNAP-06 | Phase 2 |
| SNAP-07 | Phase 2 |
| RAG-01 | Phase 1 |
| RAG-02 | Phase 1 |
| RAG-03 | Phase 1 |
| EXTRACT-01 | Phase 3 |
| EXTRACT-02 | Phase 3 |
| EXTRACT-03 | Phase 3 |
| PEER-01 | Phase 4 |
| PEER-02 | Phase 4 |
| FCAST-01 | Phase 5 |
| FCAST-02 | Phase 5 |
| FCAST-03 | Phase 5 |
| FCAST-04 | Phase 5 |
| FCAST-05 | Phase 5 |
| GMP-01 | Phase 4 |
| GMP-02 | Phase 4 |
| GMP-03 | Phase 5 |
| EVAL-01 | Phase 6 |
| EVAL-02 | Phase 6 |
| EVAL-03 | Phase 3 |
| EVAL-04 | Phase 6 |
| EVAL-05 | Phase 6 |
| TRUST-01 | Phase 1 |
| TRUST-02 | Phase 1 |
| TRUST-03 | Phase 1 |
| TRUST-04 | Phase 1 |
| UI-01 | Phase 1 |
| UI-02 | Phase 1 |
| UI-03 | Phase 5 |
| UI-04 | Phase 4 |
| OPS-01 | Phase 2 |
| OPS-02 | Phase 1 |
| OPS-03 | Phase 6 |
| METHOD-01 | Phase 3 |
| LAND-01 | Phase 6 |
| FAILGAL-01 | Phase 6 |

## Notes

This roadmap is vertical-slice MVP: every phase ships an end-to-end user-visible capability, not a horizontal technical layer. Phase 1 alone is demoable. Each subsequent phase adds another independently-demoable slice on top of the prior.

The phase progression maps onto the canonical research-identified MVP slices (ARCHITECTURE.md, SUMMARY.md):
- Phase 1 = MVP-A (cited Q&A on one IPO)
- Phase 2 = MVP-A + multi-IPO snapshot catalogue
- Phase 3 = MVP-B (adds structured extraction NLP signal)
- Phase 4 = MVP-C (adds peer comparison + historical dataset foundation)
- Phase 5 = MVP-D (adds the headline DS forecaster — the portfolio piece)
- Phase 6 = polished DRHPLens v1 (eval harness + portfolio surface)

Phase 1 must ship publicly (or at least to a Loom + repo) before Phase 2 begins. This is the most important phase gate in the project — it locks the compliance + citation infrastructure in place and proves the vertical slice works end-to-end before depth is added on any layer.

---
*Roadmap created: 2026-05-28*
