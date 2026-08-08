# Roadmap: DRHPLens

**Created:** 2026-05-28
**Mode:** MVP (vertical-slice progression)
**Granularity:** standard
**Coverage:** 45/45 v1 requirements mapped (incl. CEO-approved cherry-picks METHOD-01, LAND-01, FAILGAL-01)
**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved.

## Phases

- [ ] **Phase 1: Foundation + MVP-A (Cited Q&A on One IPO)** - End-to-end cited Q&A working on one hand-loaded DRHP with full compliance posture, citation infrastructure, and deployed demo URL.
- [x] **Phase 2: Multi-IPO Catalogue + DRHP Snapshot Surface** - Browseable catalogue of 5-10 IPOs, each with a per-IPO snapshot page (metadata, business summary, financials, risks, use of proceeds, promoter section), all DRHP-cited. (completed 2026-06-24)
- [x] **Phase 3: Structured Signal Extraction (Red-Flag Table)** - NLP-extracted structured red-flag table per IPO with per-field confidence scores, hand-labeled gold set evaluation (F1), and numeric-faithfulness release gate. (completed 2026-07-05)
- [x] **Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display** - Survivorship-corrected historical IPO dataset (SEBI-sourced universe with status column), peer multiples comparison table, GMP read-only display, Indian-context formatting throughout. (completed 2026-07-27)
- [x] **Phase 5: Calibrated Listing-Day Forecaster** - XGBoost + MAPIE conformal regression with walk-forward backtest, four baselines, committed model card, GMP-vs-model gap signal, uncertainty rendered as first-class UI. (completed 2026-07-25; honest model card — forecaster does not beat baselines, the expected D5-01 result)
- [x] **Phase 6.1: Eval Harness + Inline Metrics + Langfuse Ops** - Committed RAGAS/DeepEval/custom eval suite (faithfulness + recall@k + citation accuracy), honest inline metric surfacing on IPO pages, and Langfuse trace enrichment + failure-mode ops dashboard. (EVAL-01/02/05; alias "6a" — built first) (completed 2026-07-31; UAT 6/6, shipped PR #2 merged to main; 4 disclosed follow-ups gate a production-ready stamp only)
- [x] **Phase 6.2: Portfolio Surfaces** - "Show your work" pane, portfolio-presentable README + model card + committed HTML eval dashboards, recruiter /methodology landing page, and browseable /failures gallery. (EVAL-04/OPS-03/LAND-01/FAILGAL-01; alias "6b") (completed 2026-08-02)
- [ ] **Phase 6.3: Agent Polish + Launch Gate** - Full multi-tool LangGraph orchestration (TTL + semantic call dedup + supervisor stress-tested) and the SEBI legal-review checkpoint gating public launch. (alias "6c")

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

**Plans:** 7/7 plans executed
Plans:

- [x] 04-01-PLAN.md — Wave 0 spike: yfinance 1.5.1 pin + jugaad-data NSE endpoint validation + nightly integration test (PEER-02)
- [x] 04-02-PLAN.md — Shared `format_inr` Indian-grouping utility + app-wide adoption (fixes FLAG-FORMAT) (UI-04)
- [x] 04-03-PLAN.md — Peer data layer: PeerRecord schema + DRHP peer-SET query + per-cell source ladder + seed fixture (PEER-01, PEER-02)
- [x] 04-04-PLAN.md — GMP data layer: GmpRecord multi-source spread + GMP-02 isolation import-audit + seed fixtures (GMP-01, GMP-02)
- [x] 04-05-PLAN.md — Peer table renderer + pure-CSS glossary tooltips, wired into snapshot page (PEER-01, PEER-02, UI-04)
- [x] 04-06-PLAN.md — Read-only monochrome GMP block, last read block, cache-only (GMP-01, GMP-02, UI-04)
- [x] 04-07-PLAN.md — Survivorship-corrected historical IPO panel + ~7% median sanity-check (FCAST-03 foundation) — panel built live at 05-11 (1,378 IPOs, 5 withdrawn; median 10.2% WITHIN the [-5%, 20%] band, no survivor inflation); SC-5 sanity result surfaced on /methodology (2026-07-27)

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
  5. Every forecast feature has a verified `available_at <= T0` timestamp (issue-open day); GMP and final subscription multiples are explicitly excluded from the production `pre_apply` model — and a leakage audit is documented in the model card (FCAST-02).**Plans**: 11 plans

**Wave 1**

- [x] 05-01-PLAN.md — modeling deps + shared offline fixtures + seed forecast records

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md — survivorship-safe two-source universe merge (NSE + SEBI/withdrawn)
- [x] 05-03-PLAN.md — ForecastRecord schema + allow-list-gated load_forecast + isolation audit

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 05-04-PLAN.md — issue-structure feature matrix behind the available_at<=T0 leakage gate
- [x] 05-07-PLAN.md — cache-only forecast render (band + GMP marker + metrics strip + card link)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 05-05-PLAN.md — XGBoost-quantile + MAPIE CQR + as-of-T0 walk-forward + R2>0.5 alarm

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 05-06-PLAN.md — global coverage/MAE/per-year-RMSE metrics + per-IPO record precompute CLI

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 05-08-PLAN.md — expanded feature families (regime/DRHP/anchor) + anchor leakage audit + sector pooling + lean selection

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 05-09-PLAN.md — four baselines + inline Diebold-Mariano + P9 release gate + D5-09 abstention

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 05-10-PLAN.md — calibration plot + PIT histogram + SHAP + MODEL_CARD.md + /methodology render

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 05-11-PLAN.md — live universe build + real records/model-card regeneration + nse verify checkpoint

**UI hint**: yes

**Pitfalls owned:** P4 (lookahead bias — feature `available_at` audit, walk-forward only, R^2 > 0.5 red-flag check), P6 (regime-shift blindness — NIFTY 6M / VIX / pipeline-density regime features, per-year RMSE), P7 (small-N sector slices — N-per-sector reported, sectors < 30 pooled or hierarchical), P9 (naive baselines beat the model — four baselines + significance test as release gate), P11 (all-LLM-glue — this phase is the >=35% non-LLM modeling budget; cut agent scope before cutting modeling scope), P17 (calibration theater — empirical coverage on held-out test, conformal not parametric), P21 (UX implies advice — interval as primary visual, no green/red coding).

**Research flag:** India-IPO feature engineering from public data has no open reference implementation. Plan ~1 EDA week in notebooks at phase start before committing to the feature set.

---

### Phase 6.1: Eval Harness + Inline Metrics + Langfuse Ops

**Goal:** A retail user (and a recruiter) sees the RAG DS-rigor surface: a committed RAGAS/DeepEval/custom-citation eval suite computes RAG faithfulness + retrieval recall@k + citation accuracy, an honest system-level subset is surfaced inline on every IPO page (per-IPO line where a real gold set exists), and every agent trace is enriched via Langfuse with cost / latency / tool-call counts + a failure-mode taxonomy on an operational dashboard.
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** EVAL-01, EVAL-02, EVAL-05
**Success Criteria** (what must be TRUE):

  1. User sees RAG faithfulness, retrieval recall@k, and citation accuracy scores surfaced inline on the IPO page — an honest system-level figure across the committed eval set, with a per-IPO line where a real gold set exists (no fabricated per-IPO numbers) — computed by a committed RAGAS/DeepEval/custom-citation-metric eval suite (EVAL-01, EVAL-02).
  2. Every agent trace is captured via Langfuse (or equivalent), reviewable by the developer, with cost / latency / tool-call counts / failure-mode taxonomy surfaced on an operational dashboard (EVAL-05).

**Plans**: 6 plans in 4 waves
- [x] 06.1-01-PLAN.md — Deps (langfuse<3, deepeval) + importable eval/metrics deterministic recall@k + citation_accuracy (TDD) + pinned EvalSummary schema [W1, EVAL-01]
- [x] 06.1-02-PLAN.md — DeepEval faithfulness LLM-judge (gemini-3.5-flash, reported-not-gated, -1 sentinel) + opt-in assert_test lane [W2, EVAL-01]
- [x] 06.1-03-PLAN.md — Langfuse direct-API trace enrichment (cost/latency/tool-calls + extended failure-mode custom scores; make tracing actually work) [W2, EVAL-05]
- [x] 06.1-04-PLAN.md — Runner emits eval_summary.json + rag-eval.md (P10 interpretation + recall-floor/gold-set caveat) [W3, EVAL-01]
- [x] 06.1-05-PLAN.md — Release gate deterministic hard-gates (citation_accuracy>=0.95, recall@10>=0.85; faithfulness reported-only) [W4, EVAL-01]
- [x] 06.1-06-PLAN.md — Honest inline eval surface on IPO pages + /methodology fill (no verdict UX, provenance, P19 read-only) [W4, EVAL-02]
**UI hint**: yes
**Alias**: 6a — built first; branch `phase6/6a-eval-harness`; design doc `docs/superpowers/specs/2026-07-28-6a-eval-harness-design.md`

**Pitfalls owned:** P10 (evaluation theater — every headline metric gets interpretation paragraph + failure gallery + human spot-check of >=50 examples), P18 (agent answers without retrieving — retrieval-mandatory contract + output-schema enforcement + trace audit eval).

**Research flag:** DeepEval CI integration and Langfuse custom-score callbacks may benefit from a brief exploration spike at phase start (~1-2 days).

---

### Phase 6.2: Portfolio Surfaces

**Goal:** A recruiter reviewing the portfolio can expand a "Show your work" pane on any claim/forecast, read a methodology-forward README + forecaster model card, browse a searchable /failures gallery, and land on a deep-linkable /methodology page — with committed HTML eval dashboards per release.
**Mode:** mvp
**Depends on:** Phase 6.1
**Requirements:** EVAL-04, OPS-03, LAND-01, FAILGAL-01
**Success Criteria** (what must be TRUE):

  1. User can click "Show your work" on any claim or forecast to expand a pane revealing the retrieval query, retrieved chunks (with scores), prompt, sources used, and eval scores for that specific claim (EVAL-04 — largely delivered by METHOD-01 in Phase 3; verify coverage and extend to forecasts).
  2. The public repo contains a portfolio-presentable README (methodology-forward, paper-like), a model card for the forecaster, a failure gallery (>=10 inspected RAG / extraction / forecast failures with commentary), and committed HTML eval dashboards under `eval/reports/` per release (OPS-03).
  3. **Recruiter landing page (LAND-01, CEO-approved cherry-pick E2)**: `/methodology` deep-linkable page renders model card + methodology writeup + failure gallery link + per-IPO eval dashboard summary — the page resume deep-links land on; the Phase 1 stub link is replaced with this full implementation.
  4. **Live browseable failure gallery (FAILGAL-01, CEO-approved cherry-pick E6)**: `/failures` page renders the eval/failures gallery (≥10 documented failures across RAG / extraction / forecast surfaces) with category, query, expected vs actual, and post-mortem note — browseable and searchable, not just a markdown file in `eval/`.

**Plans**: TBD
**UI hint**: yes
**Alias**: 6b

**Pitfalls owned:** P19 (demo-day fragility — final pass: pre-index corpus, cache LLM responses, cron pinger, offline demo video).

---

### Phase 6.3: Agent Polish + Launch Gate

**Goal:** The agent is upgraded to full multi-tool LangGraph orchestration (TTL + semantic call dedup + supervisor stress-tested against weird-user-query inputs), and a SEBI legal-review checkpoint is completed before the app ships publicly.
**Mode:** mvp
**Depends on:** Phase 6.2
**Requirements:** (none new — success-criterion-driven; agentic-orchestration polish + the P1 final launch gate)
**Success Criteria** (what must be TRUE):

  1. A SEBI legal-review checkpoint has been completed before the app ships publicly (P1 final gate); the agent is upgraded to full multi-tool LangGraph orchestration with TTL + semantic call dedup + supervisor stress-tested against weird-user-query inputs (P8 mitigation).

**Plans**: 10 plans in 7 waves

**Wave 1**
- [x] 06.3-01-PLAN.md — Contracts foundation: P8 bound constants + SupervisorState superset + ToolClaim/FusedAnswer schema (D-06/D-03)

**Wave 2** *(blocked on Wave 1)*
- [x] 06.3-02-PLAN.md — Bounded LLM-classify routing hop (D-05/D-07)
- [x] 06.3-03-PLAN.md — Read-only tool nodes (peers/forecast+GMP/redflags) + semantic cache + isolation (D-01/D-04/D-06)
- [x] 06.3-04-PLAN.md — Committed adversarial stress corpus + offline stress-suite scaffold (D-07/D-09)

**Wave 3** *(blocked on Wave 2)*
- [x] 06.3-05-PLAN.md — Bounded supervisor wraps the existing graph + DRHP-only synthesis + P8 bounds (D-02/D-05/D-06/D-08)

**Wave 4** *(blocked on Wave 3)*
- [x] 06.3-06-PLAN.md — Extended cite-check (ToolClaim) + multi-tool fusion synthesis + tool-wiring (D-03/D-04/D-08)

**Wave 5** *(blocked on Wave 4)*
- [ ] 06.3-07-PLAN.md — Activate stress gate + release_gate stress lane + FAILURE_MODES (D-09/D-07/D-08)
- [ ] 06.3-08-PLAN.md — UI fused surfaces C1/C2/C3 + chat routes through the supervisor (D-03/D-04/D-08)

**Wave 6** *(blocked on Wave 5)*
- [ ] 06.3-09-PLAN.md — Public deploy guards (global cap + throttle) + C4 quota fallback + keep-warm; re-verify Gemini RPD (D-12/D-13)

**Wave 7** *(blocked on Wave 6)* — **non-autonomous (HITL launch gate)**
- [ ] 06.3-10-PLAN.md — SEBI self-audit + WR-03 dep-sync + CI gate lane + judge-calibration/gold-set/deploy HITL (D-10/D-11/D-13/D-14)

**UI hint**: yes (4 new surfaces C1–C4)
**Alias**: 6c — holds public launch

**Pitfalls owned:** P8 (agent infinite loops — TTL + semantic dedup + supervisor stress-tested), P1 final gate (SEBI legal-review checkpoint before public launch).

---

## Progress Tracking

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + MVP-A | 6/6 | Code complete (OPS-02 public deploy pending) |  |
| 2. Multi-IPO Catalogue + DRHP Snapshot | 5/5 | Complete   | 2026-06-24 |
| 3. Structured Signal Extraction | 7/7 | Complete (EVAL-03 gate PASSES 0.957) | 2026-07-25 |
| 4. Historical IPO Dataset + Peer Comparator + GMP | 7/7 | Complete (survivorship panel built live; median sanity on /methodology) | 2026-07-27 |
| 5. Calibrated Listing-Day Forecaster | 11/11 | Complete (honest model card; forecaster does not beat baselines) | 2026-07-25 |  |
| 6.1 Eval Harness + Inline Metrics + Langfuse Ops | 6/6 | Executed (verification pending) | 4 waves |
| 6.2 Portfolio Surfaces | 4/4 | Complete    | 2026-08-02 |
| 6.3 Agent Polish + Launch Gate | 6/10 | In Progress|  |

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
- **Eval hooks are instrumented from Phase 1.** Dashboard polish is Phase 6.1, but every agent run writes a full trace from day one (P10).
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
| EVAL-01 | Phase 6.1 |
| EVAL-02 | Phase 6.1 |
| EVAL-03 | Phase 3 |
| EVAL-04 | Phase 6.2 |
| EVAL-05 | Phase 6.1 |
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
| OPS-03 | Phase 6.2 |
| METHOD-01 | Phase 3 |
| LAND-01 | Phase 6.2 |
| FAILGAL-01 | Phase 6.2 |

## Notes

This roadmap is vertical-slice MVP: every phase ships an end-to-end user-visible capability, not a horizontal technical layer. Phase 1 alone is demoable. Each subsequent phase adds another independently-demoable slice on top of the prior.

The phase progression maps onto the canonical research-identified MVP slices (ARCHITECTURE.md, SUMMARY.md):

- Phase 1 = MVP-A (cited Q&A on one IPO)
- Phase 2 = MVP-A + multi-IPO snapshot catalogue
- Phase 3 = MVP-B (adds structured extraction NLP signal)
- Phase 4 = MVP-C (adds peer comparison + historical dataset foundation)
- Phase 5 = MVP-D (adds the headline DS forecaster — the portfolio piece)
- Phase 6.1/6.2/6.3 = polished DRHPLens v1 (6.1 eval harness → 6.2 portfolio surface → 6.3 agent polish + launch gate)

Phase 1 must ship publicly (or at least to a Loom + repo) before Phase 2 begins. This is the most important phase gate in the project — it locks the compliance + citation infrastructure in place and proves the vertical slice works end-to-end before depth is added on any layer.

---
*Roadmap created: 2026-05-28*
