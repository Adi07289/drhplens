# Requirements: DRHPLens

**Defined:** 2026-05-28
**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingestion (DRHP/RHP pipeline)

- [x] **INGEST-01**: System ingests DRHP/RHP PDFs from SEBI/BSE/NSE archives for the covered IPOs
- [~] **INGEST-02**: System parses 300–500 page DRHPs including financial tables, risk-factor lists, and promoter sections (table extraction quality is measured, not assumed) — code complete; live upsert pending — see data/swiggy_drhp/INGEST_LATER.md
- [~] **INGEST-03**: System indexes parsed content into a vector store with section-aware chunking suitable for long financial documents — code complete; live upsert pending — see data/swiggy_drhp/INGEST_LATER.md

### Snapshot (Per-IPO summary surface)

- [x] **SNAP-01**: User can browse the list of covered Indian mainboard IPOs (recent + currently-open)
- [x] **SNAP-02**: User sees per-IPO metadata — price band, lot size, dates, issue size, fresh-issue vs OFS split, lead managers
- [x] **SNAP-03**: User sees a plain-English business-model summary, with DRHP citation
- [x] **SNAP-04**: User sees a key-financials snapshot (3–5 year revenue, profit, margins, debt, ROE, ROCE) extracted from DRHP restated financial statements
- [x] **SNAP-05**: User sees a prioritized risk-factors summary, each cluster citing original DRHP risk text
- [x] **SNAP-06**: User sees a use-of-proceeds breakdown with OFS-vs-fresh-issue percentage highlighted
- [x] **SNAP-07**: User sees a promoter / management section (names, pre/post holdings, pledging status, prior matters) with citations

### RAG (Q&A with Citations)

- [ ] **RAG-01**: User can ask plain-English questions about a specific covered IPO and receive a grounded answer
- [ ] **RAG-02**: Every claim in an answer carries a clickable, span-level citation that anchors back to its DRHP page or peer-data source
- [ ] **RAG-03**: System refuses ungrounded queries and surfaces "This DRHP does not address X" rather than hallucinating

### Extract (NLP Structured Signals)

- [x] **EXTRACT-01**: System extracts a structured red-flag signal table per IPO: RPT % of revenue, OFS vs fresh-issue %, promoter pledge %, customer concentration (if disclosed), auditor history, debt trajectory, "going concern" mentions
- [x] **EXTRACT-02**: Each extracted field carries an extractor confidence score visible in the UI
- [x] **EXTRACT-03**: Extractors are evaluated against a hand-labeled gold set with per-field F1 reported and committed to the repo

### Peer (Peer Comparison)

- [x] **PEER-01**: System surfaces peers identified from the DRHP's own "Comparison with Listed Peers" section
- [x] **PEER-02**: System displays peer multiples (P/E, P/B, EV/EBITDA, ROE) sourced from screener.in / yfinance / NSE / BSE

### Forecast (Calibrated Listing-Day Return)

- [ ] **FCAST-01**: System produces a calibrated listing-day return range with an 80% prediction interval for each covered IPO
- [ ] **FCAST-02**: Forecast model uses only features available at T−1 of listing day; explicit `available_at` enforced (no GMP, no subscription-at-close)
- [ ] **FCAST-03**: Forecast is backtested using walk-forward CV on a historical Indian mainboard IPO universe sourced from SEBI/issuer-side filings (survivorship eliminated; includes withdrawn / delisted)
- [ ] **FCAST-04**: Forecast page displays empirical interval coverage, MAE, and per-year RMSE from the backtest
- [ ] **FCAST-05**: Forecast model card is committed to the repo (data, features, baselines, significance tests, calibration plots, limitations)

### GMP (Grey Market Premium Display)

- [x] **GMP-01**: System displays read-only GMP scraped from public aggregators, with explicit caveats about provenance and reliability
- [x] **GMP-02**: GMP is computationally isolated from the forecast model — no model feature is derived from GMP
- [ ] **GMP-03**: UI shows the gap between GMP and the GMP-free model forecast as a transparent comparative signal

### Eval (Evaluation Harness)

- [ ] **EVAL-01**: System reports RAG faithfulness, retrieval recall@k, and citation accuracy per IPO using a committed eval suite (RAGAS / DeepEval / custom citation metric)
- [ ] **EVAL-02**: A subset of eval metrics is surfaced in the UI ("This page's RAG faithfulness: 0.91", retrieval coverage, citation accuracy)
- [ ] **EVAL-03**: Numeric-faithfulness has a dedicated eval track with a release gate of ≥0.95 (no shipping below threshold)
- [ ] **EVAL-04**: A "show your work" pane reveals retrieval query, retrieved chunks, prompt, sources, and eval scores for any claim
- [ ] **EVAL-05**: Agent traces are captured via Langfuse (or equivalent) and reviewable

### Trust (Compliance & Honesty Posture)

- [x] **TRUST-01**: Persistent disclaimer + first-use modal + per-answer footer frame the product as informational / educational, never as investment advice
- [x] **TRUST-02**: A banned-token scrubber prevents prescriptive language ("subscribe", "avoid", "buy", "sell", "target", "recommend") in any generated output
- [x] **TRUST-03**: AI usage and methodology disclosure complies with SEBI January-2025 Research Analyst guidelines (font size, prominence, content)
- [ ] **TRUST-04**: A non-LLM cite-check node validates every claim against the retrieved evidence set before any answer is shown to the user

### UI (Web Frontend)

- [x] **UI-01**: Web app is mobile-responsive and renders cleanly on a phone (Indian retail is mobile-first)
- [x] **UI-02**: UI renders citations as superscript chips that expand to source-text snippets and link to the DRHP page
- [ ] **UI-03**: Uncertainty is rendered as a first-class visual element (interval widths, confidence tags, GMP-vs-model gap)
- [ ] **UI-04**: Indian-context formatting (lakh/crore numbers, INR symbols, RPT/QIB/NII/RII tooltips) is correct throughout

### Ops (Coverage & Deployment)

- [x] **OPS-01**: v1 covers 5–10 recent mainboard IPOs and 1–2 currently-open mainboard IPOs
- [ ] **OPS-02**: App is publicly deployed on a free-tier host (e.g., Hugging Face Spaces) and accessible via URL
- [ ] **OPS-03**: Repo is portfolio-presentable — README, methodology writeup, model card, failure gallery, eval dashboards committed

### Methodology Transparency (CEO-approved cherry-picks)

- [x] **METHOD-01**: "Show your work" methodology pane — expandable on any answer to reveal retrieval query, retrieved chunks with scores, prompt used, sources cited, and faithfulness/citation eval scores for that specific claim (pulled forward to Phase 3 per CEO review)
- [ ] **LAND-01**: Recruiter landing page at `/methodology` deep-linkable URL — renders model card + methodology writeup + failure gallery link + per-IPO eval dashboard summary (Phase 6, with stub link from Phase 1 home page)
- [ ] **FAILGAL-01**: Live browseable failure gallery at `/failures` page — renders ≥10 documented failures across RAG / extraction / forecast surfaces with category, query, expected vs actual, and post-mortem note (Phase 6; replaces the markdown-only file in `eval/`)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Agent Capabilities

- **AGENT-MULTI-01**: Agentic multi-step Q&A — agent decomposes complex questions ("Is this IPO overvalued?") into sub-queries across tools
- **COHORT-01**: Historical-similar-IPO cohort view (KNN over historical IPO features → empirical cohort listing-day distribution)
- **DISCLOSE-GAP-01**: "What this DRHP doesn't say" panel — expected-disclosures checklist with extraction confidence
- **POST-LIST-01**: Post-listing calibration recap pages (T+5, T+30, T+90 actuals vs forecast)

### Coverage / Automation

- **AUTO-INGEST-01**: Automated ingestion pipeline pulling new DRHPs from SEBI / exchange feeds unattended
- **MULTI-IPO-COMPARE-01**: Side-by-side comparison view across two open IPOs

### Portfolio Red-Flag Radar (the SaaS evolution)

- **PORTFOLIO-01**: User adds holdings / watchlist; same engine monitors disclosures + concalls + news for governance risks
- **PORTFOLIO-02**: Per-holding risk forecast and cited explanation (promoter pledging, holding cuts, auditor / RPT issues)

### Other v2 deferrals

- **SME-01**: SME IPO support (separate disclosure regime, separate model, clearly labeled)
- **MOBILE-NATIVE-01**: Native mobile app
- **PAID-TIER-01**: Paid SaaS subscription
- **MULTILINGUAL-01**: Multilingual UI (Hindi first, then regional languages)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| "Subscribe / Avoid" verdict | Crosses into SEBI RIA-regulated investment advice; also undercuts the entire honesty-first positioning |
| Investment-advice-style language ("you should…", "we recommend…") | Direct SEBI RIA risk; conflicts with not-advice framing |
| GMP-based forecasting / using GMP as a model feature | Circular (GMP encodes listing-day expectations), compliance optics, undermines honest positioning |
| Real-time / intraday trading signals | Wrong product for retail IPO subscribers; advice-adjacent; violates free-data constraint |
| Personalized portfolio integration (v1) | SEBI advisor-registration concerns; v2 Portfolio Red-Flag Radar territory |
| User accounts / login / personalization (v1) | No validated user value yet; adds auth + privacy obligations |
| Paid data feeds (Bloomberg, Refinitiv, paid GMP feeds) | Violates free/public-data constraint; defeats $0 portfolio-project posture |
| Ad-supported / sponsored-IPO content | Incompatible with honesty-first positioning |
| SME IPO coverage | Lighter disclosure regime, weaker signal; would degrade v1 quality bar |
| "Will I get allotted?" / allotment-probability predictor | Allotment is a lottery by SEBI rule; no real DS depth |
| Auto-refreshing live ticker / push notifications | Advice-adjacent feel; batch per-IPO is sufficient |
| Sentiment scraping from Twitter / Reddit / Telegram | Indian IPO social media is dominated by GMP touts and pumps — imports the noise we're filtering |
| Generic-LLM "finance chat" mode (no DRHP grounding) | Defeats the grounded / cited positioning |
| Mobile-native app (v1) | Web is sufficient for target user and faster to ship |
| US / foreign markets | India focus is a deliberate differentiator |

## Traceability

Which phases cover which requirements. Updated by roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Complete |
| INGEST-02 | Phase 1 | Code-complete (upsert pending) |
| INGEST-03 | Phase 1 | Code-complete (upsert pending) |
| SNAP-01 | Phase 2 | Complete |
| SNAP-02 | Phase 2 | Complete |
| SNAP-03 | Phase 2 | Complete |
| SNAP-04 | Phase 2 | Complete |
| SNAP-05 | Phase 2 | Complete |
| SNAP-06 | Phase 2 | Complete |
| SNAP-07 | Phase 2 | Complete |
| RAG-01 | Phase 1 | Pending |
| RAG-02 | Phase 1 | Pending |
| RAG-03 | Phase 1 | Pending |
| EXTRACT-01 | Phase 3 | Complete |
| EXTRACT-02 | Phase 3 | Complete |
| EXTRACT-03 | Phase 3 | Complete |
| PEER-01 | Phase 4 | Complete |
| PEER-02 | Phase 4 | Complete |
| FCAST-01 | Phase 5 | Pending |
| FCAST-02 | Phase 5 | Pending |
| FCAST-03 | Phase 5 | Pending |
| FCAST-04 | Phase 5 | Pending |
| FCAST-05 | Phase 5 | Pending |
| GMP-01 | Phase 4 | Complete |
| GMP-02 | Phase 4 | Complete |
| GMP-03 | Phase 5 | Pending |
| EVAL-01 | Phase 6 | Pending |
| EVAL-02 | Phase 6 | Pending |
| EVAL-03 | Phase 3 | Pending |
| EVAL-04 | Phase 6 | Pending |
| EVAL-05 | Phase 6 | Pending |
| TRUST-01 | Phase 1 | Complete |
| TRUST-02 | Phase 1 | Complete |
| TRUST-03 | Phase 1 | Complete |
| TRUST-04 | Phase 1 | Pending |
| UI-01 | Phase 1 | Complete |
| UI-02 | Phase 1 | Complete |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 4 | Pending |
| OPS-01 | Phase 2 | Complete |
| OPS-02 | Phase 1 | Pending |
| OPS-03 | Phase 6 | Pending |
| METHOD-01 | Phase 3 | Complete |
| LAND-01 | Phase 6 | Pending |
| FAILGAL-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 after CEO review (METHOD-01, LAND-01, FAILGAL-01 added; Traceability extended)*
