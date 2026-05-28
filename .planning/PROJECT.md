# DRHPLens

*(working name — easy to rename)*

## What This Is

DRHPLens is a web app that lets Indian retail investors ask plain-English questions about an IPO and get an honest, cited, data-grounded assessment of its DRHP/RHP — the 400-page prospectus almost nobody reads. An agentic AI system reads the prospectus, extracts the real signals (risks, financials, promoter background, related-party transactions, use of proceeds), places the company in context against listed peers, and forecasts a calibrated range for listing-day behavior based on historical Indian IPOs.

It is explicitly **informational and educational**, not investment advice.

## Core Value

Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can ask plain-English questions about a specific Indian mainboard IPO and receive a grounded, cited answer
- [ ] System ingests and indexes DRHP/RHP PDFs (300–500 pages, complex structure) from SEBI/exchanges
- [ ] Agent extracts structured signals from a DRHP: risk factors, financial snapshot, promoter background, related-party transactions, use of proceeds, business-model summary
- [ ] Agent surfaces valuation context vs listed peers (multiples comparison) using public fundamentals
- [ ] Agent produces a forecasted listing-day return range with honest uncertainty, based on historical Indian IPO data
- [ ] Every claim in an answer cites its source (DRHP page/section or peer filing) — anti-hallucination is enforced and measured
- [ ] An evaluation harness reports RAG quality (faithfulness, retrieval recall@k, citation accuracy) and forecast backtest metrics (calibration, error)
- [ ] App is deployable as a web frontend usable by a real retail investor
- [ ] UI and copy explicitly frame the product as informational/educational, never as investment advice

### Out of Scope

- US / non-Indian markets — India focus is a deliberate differentiator and aligns with the target user
- SME-segment IPOs — different disclosure regime; mainboard NSE/BSE only for v1
- "Subscribe / avoid" verdicts or any buy/sell recommendation — SEBI RIA rules + honesty-first framing forbid this
- Real-time / intraday trading signals — wrong product for the target user
- Portfolio Red-Flag Radar (governance monitoring over user holdings) — deferred to v2 SaaS evolution
- Mobile-native app — web-first for v1 (web is sufficient and faster to ship)
- Paid data subscriptions (Bloomberg, paid feeds) — free/public data only

## Context

- **Audience:** Indian retail investors — record demat-account growth, intense IPO subscription frenzy, very high vulnerability to hype. Most do not read prospectuses.
- **Document landscape:** DRHPs/RHPs are publicly filed with SEBI and the exchanges. They are 300–500-page PDFs, structurally complex (risk factors, MD&A, financial statements, RPTs, promoter background). This makes them a near-ideal RAG showcase — long, dense, public, and underserved.
- **Data fragmentation:** Indian financial data is scattered across SEBI, BSE, NSE, screener.in, company IR pages, and aggregators. There is no EDGAR-equivalent clean firehose. Building reliable ingestion is itself a data-engineering/DS signal.
- **Regulatory environment:** SEBI rules treat investment advice as a regulated activity (requires RIA registration). The honest, cited, calibrated framing is therefore both a differentiator and a compliance posture.
- **Project intent:** Portfolio piece aimed at Data Scientist (primary) and ML Engineer (secondary) roles. Goal is genuine ML/DS depth — not just LLM API gluing.
- **v2 trajectory:** The same agent infrastructure will later power a Portfolio Red-Flag Radar (governance monitoring across user holdings: promoter pledging, holding cuts, auditor/RPT issues), evolving into a SaaS investor-intelligence product.

## Constraints

- **Tech stack**: Web app frontend — Specific framework choice deferred to research phase.
- **Data**: Free/public sources only — SEBI DRHP/RHP PDFs, NSE/BSE historical IPO and price data, screener.in / IR pages for peer fundamentals, `yfinance` (`.NS`/`.BO`) for prices. No paid feeds in v1.
- **Compliance**: Informational/educational only — Required to stay outside SEBI RIA scope and to align with the honesty-first product framing.
- **Scope**: Indian mainboard IPOs (NSE/BSE) — SME segment excluded; non-Indian markets excluded.
- **DS depth**: Project must showcase real modeling — Honest forecasting with proper backtesting, evaluated NLP extraction, and rigorous RAG evaluation — not LLM-only glue code.
- **Budget**: Free / minimal-tier infrastructure — Portfolio project; cloud costs must be near-zero.
- **Audience signal**: Outputs must read as a Data Scientist's work — Evals, calibration, uncertainty, and methodology must be visible artifacts, not buried.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| India-focused (vs US) | Personal credibility (user is Indian), market is underserved by AI tooling, and differentiates from the saturated pool of US RAG-over-10K portfolio projects | — Pending |
| IPO / DRHP decoder as v1 (vs earnings analyst) | Most distinctive RAG showcase (huge PDFs nobody reads), cleanest defensible forecasting target (historical listing-day behavior), uniquely intense retail relevance in India | — Pending |
| Honesty-first framing — cited, calibrated, not-advice | Aligns DS rigor with SEBI compliance; positions the product as the antidote to hallucinating finance chatbots; core differentiator | — Pending |
| Hybrid agentic architecture (RAG + NLP extraction + peer-comparison tool + historical-IPO forecasting) | Demonstrates RAG + ML + agents together in a way that maps to a real analyst workflow | — Pending |
| v2 evolution: combine with Portfolio Red-Flag Radar into a SaaS | Same engine, broader product; shows product thinking beyond a one-shot portfolio piece | — Pending |
| Working name: "DRHPLens" | Captures the "lens onto the prospectus" value prop; rename welcomed once branding is considered | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-28 after initialization*
