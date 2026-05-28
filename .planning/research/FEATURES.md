# Feature Research

**Domain:** Indian IPO/DRHP decoder for retail investors (agentic RAG over prospectuses + historical IPO context)
**Researched:** 2026-05-28
**Confidence:** HIGH (table stakes/anti-features); MEDIUM (differentiator design specifics)

## Executive Summary

The Indian IPO information landscape is **wide but shallow**. Chittorgarh, Moneycontrol, Trendlyne, Tickertape, screener.in, Zerodha and dozens of finfluencer sites cover the *transactional* layer well — GMP, subscription, dates, allotment, basic financials, peer multiples. None of them actually *read the DRHP* for the user. The 300–500 page prospectus is universally linked-to and universally unread. Where AI tools (ChatPDF, AlphaSense, Bloomberg AskB, Perplexity, Claude Projects) do read documents, they either lack Indian-IPO domain grounding, lack honest calibration, or are gated behind enterprise pricing.

DRHPLens's defensible niche sits in the **intersection nobody owns**: domain-grounded agentic RAG over Indian DRHPs + historical-IPO-calibrated forecasting + an honesty-first UX that explicitly refuses to give a buy/sell call. This is also a **regulatory moat** — Indian retail tools shy away from showing real "analysis" because SEBI's January 2025 finfluencer/RA crackdown has made unregistered advice expensive. The "cited, calibrated, not-advice" framing is both the right DS posture and the right compliance posture.

The hard constraints for v1: zero paid data, must not look like investment advice, must showcase real ML (not just LLM glue), must work for an Indian retail investor who is not financially literate. This drives a focused MVP: pick one IPO at a time, decode it honestly, show your work.

## Feature Landscape

### Table Stakes (Users Expect These)

Features an Indian retail investor will assume exist on any IPO tool. Missing these = "this product is incomplete / why would I use this over Chittorgarh?"

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **IPO selection / search** (list of open + upcoming mainboard IPOs) | Every Indian IPO site has this; user needs to find their IPO | LOW | Pull from BSE/NSE feeds or scrape Chittorgarh/Trendlyne metadata. For v1 a small curated set (5–20 IPOs) is acceptable if cited as such. |
| **Basic IPO metadata pane** (price band, lot size, dates, issue size, fresh issue vs OFS split, lead managers) | Universal "above the fold" on every Indian IPO page | LOW | Structured fields; either scraped or extracted from RHP cover page. |
| **Plain-English business model summary** | The whole point — user can't / won't read the DRHP | MEDIUM | LLM extraction from "Our Business" / MD&A; must cite DRHP page. Avoid marketing-copy paraphrase. |
| **Key financials snapshot** (3–5 year revenue, profit, margins, debt, ROE, ROCE) | Retail investor's first sanity check; every tool shows this | MEDIUM | Extract from "Restated Financial Statements" tables in DRHP. Table parsing in Indian DRHPs is non-trivial. Show both growth trajectory and absolute numbers. |
| **Risk factors, summarized and prioritized** | The DRHP's most important section; retail investors never read all 100+ risks | MEDIUM | DRHPs already list risks in roughly severity order — preserve that. LLM clusters/summarizes, retains page citations to original risk text. |
| **Use of proceeds breakdown** | Retail investor wants to know "where is my money going" — debt repayment vs growth vs OFS-cash-out is *the* signal | LOW | Structured extraction from "Objects of the Issue" section. Highlight % going to OFS (insider cash-out) vs fresh issue. |
| **Promoter / management section** | Trust check; retail expects to see who's behind the company | MEDIUM | Names, holdings pre/post IPO, pledging status, prior criminal/regulatory matters. DRHP discloses all of this; tool surfaces it cleanly. |
| **Peer comparison** (P/E, P/B, EV/EBITDA, ROE vs listed peers in same sector) | Tickertape/screener.in have set this expectation — every Indian investor expects multiples context | MEDIUM | Free data via screener.in scrape or yfinance fundamentals (`.NS`/`.BO`). Identify peers from DRHP's own "Industry" and "Comparison with Listed Peers" sections — DRHPs are required to disclose comparable listed peers. |
| **Plain-English Q&A over the DRHP** | The core value prop, but also "table stakes" in the sense that any "AI for IPO" product MUST have a chat interface that works | HIGH | RAG with citations. Sub-bullet table-stakes: clickable citations that anchor back to the DRHP page (a la ChatPDF, Perplexity). |
| **Citations on every claim** | Post-Perplexity, users now expect inline citations from any AI assistant | MEDIUM | Anchor each generated sentence to a DRHP page/section ID. UI: superscript citation chips that expand to source text. |
| **GMP / subscription status display** (read-only, with caveats) | Indian retail's #1 question is "what's the GMP?" — refusing to show it makes the product feel hostile | LOW–MEDIUM | Scrape from public GMP aggregators (Chittorgarh, IPO Watch, InvestorGain). Display with explicit warning that GMP is informal grey-market chatter, ~80% correlated with listing return on mainboard, frequently wrong. Do NOT integrate GMP into the forecast model — show it next to the model output and let the user compare. |
| **Mobile-responsive web UI** | Indian retail = mostly mobile; even though we're "web first not mobile native" the web must work on a phone | LOW | Tailwind / responsive defaults; not a separate codebase. |
| **Disclaimer / not-advice framing** (visible, not buried) | SEBI compliance + product positioning — retail users have actually become wary post-finfluencer crackdown | LOW | Persistent footer + first-use modal + per-answer footer. Wording matters; should feel like a feature, not a CYA. |
| **Anti-hallucination behavior** ("I don't know" when the DRHP doesn't say) | Expected of any modern grounded-AI product; retail users have been burned by hallucinating chatbots | MEDIUM | Refusal patterns + answer-faithfulness scoring + UI surface ("This DRHP does not address X"). |

### Differentiators (Competitive Advantage)

These are where DRHPLens earns its place over Chittorgarh, Tickertape, ChatPDF, and a Perplexity-with-a-PDF. They also are where the **DS portfolio signal** lives.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Agentic Q&A with multi-step reasoning** | Beyond "find passage and quote" — agent decomposes "Is this IPO overvalued?" into sub-queries (extract P/E from DRHP financials, fetch peer P/Es, compute z-score, return with caveats) | HIGH | This is the hard ML/agent work. Differentiates from ChatPDF (single-doc retrieval) and from Chittorgarh (no reasoning). |
| **Calibrated listing-day return range** ("Median listing return for IPOs with this profile was +8%; 80% prediction interval: −12% to +35%") | Direct response to GMP's 0.8 correlation but high error variance. Honest about uncertainty in a market where every other tool gives spurious precision | HIGH | Conformal prediction or quantile regression on historical Indian IPO features. **Critical:** features must NOT include GMP (data-leakage / circular); use DRHP/peer features only. Backtest required. |
| **Structured-signal table (NLP-extracted)** — auto-generated red-flag table: customer concentration %, RPT as % of revenue, % OFS vs fresh, promoter pledge %, auditor history, debt trajectory, "going concern" mentions | Surfaces the *actual* analyst signal that retail investors miss in the 400-page document. No Indian tool does this comprehensively today. | HIGH | NLP extraction pipeline with per-field evaluation. The eval/F1 numbers per field become a portfolio artifact. |
| **"Show your work" methodology pane** | One-click expansion on any claim or forecast that shows: retrieval query, retrieved chunks, prompt, sources used, eval scores. Pure DS-rigor signal | MEDIUM | UI feature on top of well-instrumented agent traces. Demonstrates the *engineering* discipline as much as the model. |
| **RAG eval transparency** (faithfulness, citation accuracy, retrieval recall@k visible as metrics in UI) | "This answer scored 0.91 faithfulness" — surfaces eval results to users. No consumer tool does this; AlphaSense doesn't either | MEDIUM | Pre-compute per-IPO retrieval/eval metrics; expose as a transparency panel. |
| **Honest uncertainty UI** (prediction intervals shown as ranges with visual width = uncertainty; "high confidence" / "low confidence" tags per answer) | The whole product differentiator — uncertainty as a first-class UI element, not buried disclaimer | MEDIUM | Conformal intervals from forecast model + a confidence classifier on Q&A answers (low when retrieval scores low or sources disagree). |
| **Comparison to historical similar IPOs** ("Among IPOs in last 5 years with similar sector, OFS %, P/E premium, and subscription pattern: 14 IPOs. Listing-day median +6%. 5 outperformed broader market over 6 months, 9 underperformed.") | Empirical anchoring; not just a forecast number but the actual historical cohort. Highly defensible. | HIGH | Requires historical IPO dataset with feature extraction. Strong DS narrative — KNN/cohort retrieval over IPOs. |
| **Anti-hallucination guardrails as a measurable feature** | Refusal rate, faithfulness floor enforced, claims-without-citation blocked — surfaced as live metrics | MEDIUM | Engineering discipline + UI badge ("0 unsupported claims in this answer"). |
| **Domain-specific extractors** (RPT-network parser, "objects of the issue" parser, peer-comparison-table parser) | Generic ChatPDF can't reliably parse the structured tables in Indian DRHPs (RPT disclosures, P&L tables, capitalization statements). Domain extractors do this with measured accuracy | HIGH | The "real ML, not glue" depth. Per-extractor evaluation against hand-labeled gold set. |
| **"What this DRHP doesn't say" panel** | Highlights *absence* of expected disclosures (e.g., no segment-wise revenue, no customer concentration disclosure, sparse RPT detail) — absence is itself signal | MEDIUM | Checklist of expected DRHP fields → which were extractable with high confidence vs absent/unclear. |
| **Indian-context grounding** (lakh/crore numbers, INR formatting, SEBI/exchange terminology, RPT/QIB/NII/RII vocabulary) | Generic AI tools mangle Indian numerical formatting and regulatory vocabulary. A small detail with outsized polish signal | LOW | Locale-aware formatters + glossary tooltips. Easy win. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like obvious wins but should explicitly **not** be built. Most are SEBI-related; some are product-positioning related; some are scope discipline.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **"Subscribe / Avoid" verdict** | Every finfluencer YouTube channel does this; user emotionally wants the answer | Crosses directly into SEBI RIA-regulated investment advice. SEBI has actively pulled 15,000+ finfluencer pieces of content. Also undercuts the entire honesty-first positioning — once you give a verdict, every other "honest" thing you say becomes window-dressing on the verdict. | Show the structured signal table + calibrated forecast range + historical cohort. Let the user form a view. The product's value is *the analysis*, not *the conclusion*. |
| **Real-time / intraday trading signals** | "What's the stock doing right now?" feels modern | Wrong product for the audience (retail IPO subscribers aren't day traders), real-time price feeds blow the free-data constraint, and signal-like outputs are advice-adjacent | Educational post-listing recap pages (T+5, T+30, T+90 performance vs forecast — useful for calibration/eval, not for trading). |
| **GMP-based forecasting / "Will it list above GMP?"** | Retail user's instinct ("what does the grey market say?") | (1) GMP is informal grey-market data of dubious provenance, (2) using GMP as a forecast feature is circular — GMP itself encodes listing-day expectations, so a model trained on it is just smoothing GMP, not adding signal. (3) Compliance-wise, building a model around informal grey-market data is poor optics. | Display GMP read-only with explicit caveats; show the model's GMP-free forecast next to it; the *gap* between model and GMP is itself an interesting honest signal. |
| **Personalized portfolio integration** ("based on your holdings…") | Feels like a natural product extension | This is Portfolio Red-Flag Radar territory — out of scope for v1, explicit in PROJECT.md. Adding it now triggers SEBI advisor-registration concerns (personalized = advice) and balloons scope. | Defer to v2 as planned. |
| **User accounts / login / personalization** | "Standard SaaS expectation" | Adds auth complexity, data-privacy obligations, no validated user value yet for v1. The IPO + the DRHP are both public; no per-user state is required. | Anonymous public web app. Persist per-IPO computed artifacts server-side; no per-user data. |
| **Paid-data feed integration** (Bloomberg, Refinitiv, paid GMP feeds) | "Better data = better product" | Violates the free/public-data constraint in PROJECT.md; defeats the cost-zero portfolio-project posture; doesn't help DS-depth signal. | Free public sources only — SEBI, NSE/BSE, screener.in, yfinance, public GMP aggregators. |
| **SME IPO coverage** | "More IPOs = more usage" | Explicit out-of-scope in PROJECT.md. SME disclosure regime is different (lighter), GMP signal is much weaker (~21% correlation vs ~80% on mainboard), and quality bar is much lower — would *degrade* the product's signal/forecast quality. | Mainboard NSE/BSE only for v1. Could add SME in v2 with a *separate, clearly-labeled* model. |
| **Ad-supported / sponsored-IPO content** | Obvious monetization path Chittorgarh and IPO Watch use | Fundamentally incompatible with honesty-first positioning. Any "sponsored" content kills the product's only differentiator. | Portfolio-piece for v1, paid SaaS for v2 (no ads). |
| **Investment-advice-style language** ("you should consider…", "this looks attractive…", "we recommend…") | Sounds more "useful" to a retail user; mimics finfluencer voice | Direct SEBI RIA violation risk. Also undercuts honest framing. | Descriptive language only: "The DRHP discloses X." "The historical cohort showed Y." "The model's 80% prediction interval is Z." Never prescriptive. |
| **"Will I get allotted?" / allotment-probability predictor** | Retail users genuinely want this | Allotment is a lottery process by SEBI rule; any predictor is either (a) literally just subscription ratio with a wrapper (already shown by every Indian IPO tool) or (b) misleading because outcome is stochastic by regulation. Adds no real DS depth. | Just show subscription multiples (table stakes) with explanation of the lottery mechanism. |
| **Auto-refreshing live ticker / push notifications** | "Modern fintech" feel | Push notifications start to feel like trading signals; live ticker tempts re-architecting for stream/real-time when batch per-IPO processing is sufficient. | Per-IPO snapshot pages, updated when DRHP/RHP or subscription data changes. Daily cron is sufficient. |
| **Sentiment scraping from Twitter / Reddit / Telegram for IPOs** | "Social signal!" — every fintech wants this | Indian IPO Twitter/Telegram is dominated by GMP touts and pump groups — scraping it would import the exact noise the product is meant to filter out. Also dubious provenance, possible TOS issues. | The honest signal *is* the absence of social hype — the structured DRHP-derived table. |
| **Generic-LLM "chat with finance" mode** (open-ended, no DRHP grounding) | Reads as "an LLM can answer anything" | Defeats the entire grounded/cited positioning. The product is *not* a general finance chatbot; once it answers ungrounded, every answer becomes suspect. | Always require an IPO context. If user asks an off-DRHP question, refuse with link to RBI/SEBI educational resources. |

## Feature Dependencies

```
DRHP ingestion + parsing (PDF → structured chunks + tables)
    └──required-by──> Plain-English business summary
    └──required-by──> Risk factors summarization
    └──required-by──> Key financials snapshot
    └──required-by──> Use of proceeds breakdown
    └──required-by──> Promoter/management section
    └──required-by──> Structured-signal table (NLP extraction)
    └──required-by──> "What this DRHP doesn't say" panel
    └──required-by──> Plain-English Q&A (RAG)

Plain-English Q&A (RAG with citations)
    └──required-by──> Agentic multi-step Q&A
    └──required-by──> "Show your work" methodology pane
    └──required-by──> Honest uncertainty UI (Q&A confidence)

Citations on every claim
    └──required-by──> Anti-hallucination guardrails (measurable)
    └──required-by──> RAG eval transparency

Historical Indian IPO dataset (features + outcomes)
    └──required-by──> Calibrated listing-day return range
    └──required-by──> Comparison to historical similar IPOs

Peer fundamentals data (screener.in / yfinance)
    └──required-by──> Peer comparison
    └──required-by──> Calibrated listing-day return range (peer multiples as features)

Structured-signal table
    └──enhances──> Plain-English Q&A (agent can cite structured signals)
    └──enhances──> Calibrated forecast (signal table feeds model features)

Disclaimer / not-advice framing
    └──conflicts-with──> "Subscribe/Avoid" verdict (mutually exclusive product positions)
    └──conflicts-with──> Investment-advice-style language
    └──conflicts-with──> Personalized portfolio integration

GMP display (read-only)
    └──conflicts-with──> GMP-based forecasting (must be kept separate for honesty + non-circularity)
```

### Dependency Notes

- **DRHP ingestion is the universal upstream.** Almost every visible feature depends on PDF parsing + structured extraction working. This makes ingestion robustness the highest-leverage early investment. Indian DRHP PDFs are inconsistently formatted across merchant bankers — table extraction in particular is hard and quality-defining.
- **Citations gate everything user-facing.** Without per-claim citations, the anti-hallucination, eval-transparency, and "show your work" differentiators collapse. Treat citation infrastructure as core, not garnish.
- **Historical IPO dataset is the forecast moat.** The calibrated-range differentiator is impossible without a clean historical dataset of (DRHP-derived features) → (listing-day outcomes). This is itself a significant data-engineering artifact and should be built before the forecast model.
- **GMP must be displayed but isolated from the model.** Showing GMP is table stakes for Indian retail. Using GMP as a forecast feature is an anti-pattern (circular, undermines honest positioning). Keep them on the same page but in separate computational pipelines.
- **Disclaimer framing is product-defining, not boilerplate.** It conflicts with verdicts and advisory language by design — meaning these features are mutually exclusive product directions. Pick the honest path and commit.
- **The structured signal table enhances both Q&A and forecast.** Once you've NLP-extracted the signal fields, they should feed (a) the user-visible red-flag table, (b) the agent's tool-use surface ("agent, look up RPT %"), and (c) the forecast model's feature vector. Build once, use three ways.

## MVP Definition

### Launch With (v1)

The smallest cut that demonstrates the full agentic-RAG + DS-rigor story end-to-end for **one IPO at a time**.

- [ ] **DRHP ingestion + chunking + indexing** — without this nothing else works.
- [ ] **Per-IPO snapshot page** — basic metadata, business summary, financials snapshot, risk factors summary, use of proceeds, promoter section. Each field cites DRHP page. (Table stakes; absence is fatal.)
- [ ] **Peer comparison block** — DRHP-disclosed peers + free-source fundamentals (P/E, P/B, ROE, EV/EBITDA). Sourced from screener.in or yfinance.
- [ ] **Plain-English Q&A with citations** — the chat surface. Single-IPO context. RAG with anchored, clickable citations.
- [ ] **Structured-signal table (red-flag extraction)** — RPT %, OFS vs fresh-issue %, customer concentration if disclosed, promoter pledge %, going-concern mentions, auditor turnover, debt trajectory. Each field has a confidence score from the extractor.
- [ ] **Calibrated listing-day return range** — model trained on historical mainboard IPOs (last 5–10 years). Conformal/quantile-style prediction interval. No GMP as feature. Backtest visible.
- [ ] **GMP display (read-only, sourced + caveated)** — shown next to the model forecast, never blended in.
- [ ] **Citation infrastructure end-to-end** — every claim anchors to a DRHP page or peer-data source.
- [ ] **Anti-hallucination guardrails** — refusal on ungrounded asks; faithfulness threshold enforced.
- [ ] **Eval harness with visible metrics** — RAG faithfulness, retrieval recall@k, citation accuracy, forecast calibration / MAE / interval coverage. Surface a subset in the UI ("This page's RAG faithfulness: 0.91").
- [ ] **Not-advice framing throughout** — persistent footer, first-use modal, per-answer note, no prescriptive language anywhere in the product copy.
- [ ] **Mobile-responsive web UI** — single-page-app or server-rendered, looks fine on a phone.
- [ ] **Coverage: 5–10 recent + 1–2 currently-open mainboard IPOs** — enough to demo and to validate. Not "all IPOs ever."

### Add After Validation (v1.x)

Add once the core surface is shipping and gets real eyes on it.

- [ ] **Agentic multi-step Q&A** — once base RAG works reliably; agent that decomposes complex questions and uses extractor tools. *Trigger: faithfulness > 0.85 on hand-labeled gold Q&A set.*
- [ ] **Comparison to historical similar IPOs (cohort view)** — KNN over historical IPO features. *Trigger: historical dataset reaches sufficient size + clean features.*
- [ ] **"Show your work" methodology pane** — expand-to-see-trace UI on any claim. *Trigger: agent traces are instrumented end-to-end.*
- [ ] **"What this DRHP doesn't say" panel** — expected-disclosures checklist with extraction confidence. *Trigger: extractor evaluations are mature enough that "absent" is reliably distinguishable from "extractor failed."*
- [ ] **Post-listing calibration recap pages** (T+5, T+30, T+90 actuals vs predicted) — useful for honest self-evaluation and as visible eval artifacts. *Trigger: 3+ months of post-launch listings to score.*
- [ ] **Broader IPO coverage** — automated ingestion pipeline pulling new DRHPs from SEBI/exchange feeds. *Trigger: ingestion is robust enough for unattended runs.*

### Future Consideration (v2+)

- [ ] **Portfolio Red-Flag Radar** — governance monitoring over user holdings (promoter pledging changes, RPT spikes, auditor changes, holding cuts). Explicit v2 trajectory in PROJECT.md. Defer: requires user accounts, broader corporate-filings ingestion, and product positioning shift from "informational" to "monitoring" — separate milestone.
- [ ] **SME IPO support** — separate model + separate disclosure regime. Defer: signal quality is lower, would dilute the v1 quality bar; also a separate compliance posture.
- [ ] **Mobile native app** — explicitly deferred in PROJECT.md. Defer: web is sufficient for the target user and faster to ship; native is a packaging concern post-PMF.
- [ ] **Multi-IPO comparison view** ("compare these two open IPOs side-by-side") — interesting feature but requires solid single-IPO surface first.
- [ ] **Subscription-based SaaS tier** — paid features for the v2 monetization arc. Defer: needs validated user value first.
- [ ] **Multilingual UI** (Hindi at minimum, then Tamil/Telugu/Bengali/Marathi) — high-value for Indian retail reach but requires the English version to be solid first and adds translation QA overhead.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| DRHP ingestion + chunking + indexing | HIGH | HIGH | **P1** |
| Per-IPO snapshot page (metadata, business, financials, risks, use of proceeds, promoter) | HIGH | MEDIUM | **P1** |
| Plain-English Q&A with citations (RAG) | HIGH | HIGH | **P1** |
| Citation infrastructure end-to-end | HIGH | MEDIUM | **P1** |
| Structured-signal table (NLP extraction) | HIGH | HIGH | **P1** |
| Calibrated listing-day return range | HIGH | HIGH | **P1** |
| Peer comparison block | HIGH | MEDIUM | **P1** |
| Anti-hallucination guardrails (measurable) | HIGH | MEDIUM | **P1** |
| Eval harness with visible metrics | HIGH | MEDIUM | **P1** |
| Not-advice framing throughout | HIGH | LOW | **P1** |
| GMP display read-only | MEDIUM | LOW | **P1** |
| Mobile-responsive UI | HIGH | LOW | **P1** |
| Agentic multi-step Q&A | HIGH | HIGH | **P2** |
| Historical cohort comparison view | HIGH | HIGH | **P2** |
| "Show your work" methodology pane | MEDIUM | MEDIUM | **P2** |
| Honest uncertainty UI (confidence chips on Q&A) | MEDIUM | MEDIUM | **P2** |
| "What this DRHP doesn't say" panel | MEDIUM | MEDIUM | **P2** |
| Broader IPO coverage (automated ingestion) | MEDIUM | MEDIUM | **P2** |
| Post-listing calibration recap | MEDIUM | LOW | **P2** |
| RAG eval transparency in UI | MEDIUM | LOW | **P2** |
| Indian-context formatters (lakh/crore, glossary) | LOW | LOW | **P3** |
| Multi-IPO side-by-side comparison | MEDIUM | MEDIUM | **P3** |
| Hindi / multilingual UI | HIGH (long-term) | HIGH | **P3 (v2+)** |
| Portfolio Red-Flag Radar | HIGH (different audience) | HIGH | **v2** |
| SME IPO coverage | MEDIUM | MEDIUM | **v2** |

**Priority key:**
- **P1** — Must ship in v1; absence breaks the value proposition.
- **P2** — Should add post-launch; enhances differentiation but not blocking.
- **P3** — Nice-to-have polish.
- **v2** — Explicitly deferred per PROJECT.md.

## Competitor Feature Analysis

| Feature | Chittorgarh | Trendlyne | Tickertape / screener.in | ChatPDF / Claude Projects | AlphaSense (enterprise) | **DRHPLens (our approach)** |
|---------|-------------|-----------|--------------------------|---------------------------|------------------------|------------------------------|
| IPO metadata + dates + GMP | Best-in-class | Good | Limited | N/A | N/A | **Table stakes parity (sourced from public feeds)** |
| DRHP document linked | Yes (PDF link only) | Yes (PDF link only) | No | User uploads | Yes | **Yes, plus actually decoded** |
| DRHP read by the tool | No | No | No | Yes (generic) | Yes (generic finance) | **Yes, with Indian-IPO-domain extractors** |
| Peer comparison (multiples) | Limited | Decent | Best-in-class | N/A | Yes (US-centric) | **Table stakes parity, DRHP-grounded peer set** |
| Risk-factor summary | No (just shows the section) | No | No | Yes (generic) | Yes (generic) | **Yes, prioritized + cited + measured extraction** |
| Red-flag extraction (RPT %, OFS %, pledge %, customer concentration) | No | No | No | No (would require prompting) | Partial (US filings) | **Yes, NLP-extracted with per-field eval** |
| Q&A over the DRHP | No | No | No | Yes (no Indian context) | Yes | **Yes, India-grounded, multi-step agent** |
| Citations | N/A | N/A | N/A | Yes | Yes | **Yes, with measured citation accuracy** |
| Listing-day forecast | No (just shows GMP) | No (just shows GMP) | No | No | No | **Yes, calibrated range with intervals, GMP-free** |
| Historical-cohort comparison | No (just lists past IPOs) | No | No | No | Partial | **Yes, KNN over historical Indian IPOs** |
| Show-your-work / RAG transparency | No | No | No | No | No | **Yes, visible eval metrics + traces** |
| "Subscribe/avoid" verdict | Yes (via aggregated reviews) | Yes (broker reports) | Yes (broker reports) | No | No | **Deliberately not built** |
| India-retail framing | Yes | Yes | Yes | No | No | **Yes, plus DS rigor on top** |
| Anti-hallucination guardrails | N/A | N/A | N/A | Partial | Better | **First-class, measured feature** |
| Pricing | Free / ad-supported | Freemium | Freemium (₹4,999/yr premium) | Free / paid | Enterprise only | **Free portfolio-piece (v1)** |

**Strategic positioning takeaway:** No existing tool actually reads the DRHP and tells the retail investor what's in it with honest uncertainty. The gap is real and ownable. The closest analogs (AlphaSense, Bloomberg AskB) are enterprise-priced and US-centric. The closest Indian tools (Chittorgarh, Trendlyne) are document-aggregator-and-GMP-bulletin-board. ChatPDF/Claude Projects can read a single PDF but lack domain grounding, peer data, historical context, and forecast calibration.

## SEBI / Compliance Constraints Honored

Every product decision above respects these constraints:

1. **No buy/sell/hold verdict anywhere in the product.** Verdicts are RIA-regulated. Replaced with descriptive analysis + calibrated forecast range + historical cohort.
2. **No prescriptive language.** All copy is descriptive ("the DRHP discloses…", "the model's 80% interval is…") never prescriptive ("you should…").
3. **Persistent informational/educational framing.** First-use modal, persistent footer, per-answer footer. Not buried.
4. **AI disclosure.** SEBI 2024 amendments mandate disclosure of AI usage in advisory contexts; the product is not advisory, but we still disclose AI usage explicitly because the user deserves to know and the disclosure is a feature, not a liability.
5. **No engagement with finfluencer signal.** No social-sentiment scraping, no GMP-Telegram-channel ingestion, no influencer integration. SEBI removed 15,000+ such content pieces in 2024–2025.
6. **No personalized advice.** No user accounts, no holdings-aware suggestions. Same output for every visitor on a given IPO.
7. **Free public-data sources only.** Aligned with both the project budget constraint and avoiding any data-licensing surprise.

## India-Retail Mental Model Reflected

These design choices specifically reflect the Indian retail investor's mental model (not a generic US-retail port):

- **GMP is unavoidable.** Indian retail's first question on any IPO is "kya GMP hai?" — hiding it would feel arrogant. Including it (read-only, caveated, *isolated from the model*) shows respect for the user's mental model while still teaching honest framing.
- **Lakh/crore native.** ₹15,000 crore is the unit a retail user thinks in, not "$1.8B." All financial display defaults to lakh/crore; toggleable to international units.
- **OFS-vs-fresh-issue prominence.** "Promoter cash-out vs growth capital" is the single most-asked Indian-retail question after GMP. Foreground it.
- **QIB/NII/RII subscription breakdown.** Retail expects to see the three categories separately — they read QIB subscription as a smart-money proxy (correctly or not).
- **Promoter scrutiny is cultural.** Indian retail investing has a deep "who is the promoter" instinct (often more than financials). Make the promoter section prominent, with prior regulatory matters surfaced if disclosed.
- **Sectoral context.** Indian retail thinks in sectors ("auto-ancillaries," "specialty chemicals," "QSR"). Peer comparison should be sector-anchored using DRHP-disclosed peers.
- **Trust deficit toward AI in finance.** Post-finfluencer-crackdown, Indian retail is wary of AI giving stock advice. Honest framing isn't just compliance — it's product trust.

## Sources

### Indian IPO ecosystem
- [Chittorgarh Mainboard IPO Dashboard](https://www.chittorgarh.com/ipo/ipo_dashboard.asp)
- [Chittorgarh on GMP / Grey Market Premium](https://www.chittorgarh.com/book-chapter/ipo-grey-market-gmp/28/)
- [Trendlyne IPO Dashboard help docs](https://help.trendlyne.com/support/solutions/articles/84000372483-what-can-i-find-on-the-ipo-dashboard-)
- [Trendlyne IPO Research Reports](https://trendlyne.com/research-reports/ipo/)
- [Tickertape — main product page](https://www.tickertape.in/)
- [Tickertape — 5 Parameters to Analyse an IPO](https://www.tickertape.in/blog/5-parameters-to-analyse-an-ipo/)
- [Tickertape Review (Strike.money)](https://www.strike.money/reviews/tickertape)
- [Screener.in main site](https://www.screener.in/)
- [Winvesta — Fundamental analysis tools and screeners: 2026 guide for India](https://www.winvesta.in/blog/investors/fundamental-analysis-tools-and-screeners-2026-guide)
- [Zerodha — Upcoming IPOs](https://zerodha.com/ipo/)
- [Zerodha invests in Tijori Finance (Inc42)](https://inc42.com/buzz/zerodha-invests-5-mn-in-investment-research-platform-tijori/)
- [Tijori Finance features](https://www.tijorifinance.com/features/)

### DRHP structure and red flags
- [Gretex — Understanding DRHP: Complete Guide to India's IPO Investors](https://gretexcorporate.com/understanding-drhp-complete-guide-to-indias-ipo-investors/)
- [IPOMarket.in — How to Read IPO DRHP in 10 Minutes](https://www.ipomarket.in/news/what-is-drhp-and-how-to-read-it)
- [Angel One — What is DRHP](https://www.angelone.in/knowledge-center/ipo/what-is-drhp-find-out-here)
- [Inventiva — Laxyo IPO DRHP red flags case study](https://www.inventiva.co.in/stories/detailed-analysis-of-debt-ridden-laxyo-limited-ipo-issues-red-flags-in-drhp/)
- [Business Standard — India's IPO jargon decoded](https://www.business-standard.com/markets/ipo/india-s-ipo-jargon-decoded-what-fresh-issue-ofs-and-drhp-really-mean-126051800207_1.html)

### GMP and listing-day prediction
- [IPO Guru — GMP vs Subscription Data Which Predicts Listing Gains Better](https://www.ipoguru.in/blog/ipo-gmp-vs-subscription-data-which-predicts-listing-gains-better)
- [arXiv — Experimenting with Multi-modal Information to Predict Success of Indian IPOs](https://arxiv.org/html/2412.16174v1)
- [Sahi — Grey Market Premium accuracy](https://www.sahi.com/blogs/grey-market-premium-in-ipo-what-it)
- [IPO Watch — IPO Listing Gains: How to Predict & Maximize Returns](https://ipowatch.in/ipo-listing-gains-how-to-predict-maximize-returns/)

### AI document tools and citation patterns
- [ChatPDF main site](https://www.chatpdf.com/)
- [Anthropic Claude (citations feature)](https://www.anthropic.com/claude)
- [ZipTie.dev — How Perplexity AI Answers Work: Retrieval, Ranking, and Citation Pipeline](https://ziptie.dev/blog/how-perplexity-ai-answers-work/)
- [AItoolland — Perplexity AI Search Engine: Can RAG Fix AI Hallucinations?](https://aitoolland.com/perplexity-ai-search-engine/)
- [Microsoft — Confidence-Aware RAG: Teaching Your AI Pipeline to Acknowledge Uncertainty](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/confidence-aware-rag-teaching-your-ai-pipeline-to-acknowledge-uncertainty/4515061)
- [Unite.AI — Sixteen Major Problems With RAG Systems (incl. Perplexity)](https://www.unite.ai/new-research-finds-sixteen-major-problems-with-rag-systems-including-perplexity/)

### Enterprise equity-research analyst tools
- [AlphaSense — Financial Research Platform](https://www.alpha-sense.com/solutions/financial-research-platform/)
- [AlphaSense — Top AI Tools for Financial Research](https://www.alpha-sense.com/resources/research-articles/ai-tools-for-financial-research/)
- [ThirdBridge — 5 Best AI tools for investment research in 2026](https://www.thirdbridge.com/en-us/about-us/media/perspectives/ai-tools-investment-research)
- [Bloomberg AskB innovations (via AlphaSense competitive piece)](https://www.thirdbridge.com/en-us/about-us/about-us/media/perspectives/alphasense-alternatives)

### SEBI compliance and finfluencer regulations
- [ELP Law — SEBI amends and modernises Investment Adviser Regulations](https://elplaw.in/leadership/sebi-amends-and-modernises-the-investment-adviser-regulations/)
- [Moneylife — SEBI's updated guidelines for Research Analysts & Investment Advisers](https://www.moneylife.in/article/sebis-updated-guidelines-for-research-analysts-and-investment-advisers-impose-more-compliance-burden/76060.html)
- [BusinessToday — SEBI tweaks regulations for finfluencers, removes 15,000+ entities](https://www.businesstoday.in/personal-finance/investment/story/sebi-tweaks-regulations-for-finfluencers-removes-content-of-over-15000-unregulated-entities-443789-2024-08-31)
- [Angel One — SEBI Issues Further Clarifications on Finfluencer Regulations](https://www.angelone.in/news/market-updates/sebi-issues-further-clarifications-on-finfluencer-regulations)
- [NLIU Law Review — SEBI's Crackdown on Finfluencers](https://nliulawreview.nliu.ac.in/blog/sebis-crackdown-on-finfluencers-a-legal-and-regulatory-perspective/)
- [TheFinanceStory — SEBI new rules on unregistered finfluencers](https://thefinancestory.com/sebi-new-rules-to-curb-unregistered-finfluencers)

### Retail behavior, IPO returns, calibration
- [NISM — IPO Flipping, Risky Trading & Debt: Young Investors](https://www.nism.ac.in/ipo-flipping-risky-trading-and-debt-the-dangerous-game-young-indian-investors-are-playing/)
- [Margin0fSafety — The (Pre) IPO Illusion](https://margin0fsafety.substack.com/p/the-pre-ipo-illusion-why-retail-investors)
- [PMC — Decoding Investor Sentiments in the Indian Stock Market](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12107233/)
- [Nixtla — Conformal Prediction tutorial](https://nixtlaverse.nixtla.io/statsforecast/docs/tutorials/conformalprediction.html)
- [Atrium — Accounting for Uncertainty: Interval-Based Forecasts](https://atrium.ai/resources/accounting-for-uncertainty-driving-forecasting-value-with-interval-based-forecasts/)

---
*Feature research for: Indian-IPO DRHP-decoder web app (DRHPLens)*
*Researched: 2026-05-28*
