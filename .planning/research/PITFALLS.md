# Pitfalls Research — DRHPLens

**Domain:** Agentic-RAG over Indian DRHPs + listing-day forecasting + DS portfolio piece
**Researched:** 2026-05-28
**Confidence:** HIGH for SEBI / survivorship / RAG-evaluation pitfalls (multiple sources + official docs). MEDIUM for India-specific data-source instability (vendor-specific, observed but not deeply documented). MEDIUM for "DS portfolio framing" pitfalls (industry consensus, not formal research).

This file enumerates the *specific* ways a project like DRHPLens silently breaks. Every pitfall is tagged with severity, warning signs, prevention, and the phase that should own preventing it.

Severity definitions used throughout:

- **CRITICAL** — Kills the project as a portfolio piece (legal, integrity, or "the whole thing is wrong" problem). Cannot be retrofitted; must be designed against.
- **HIGH** — Causes a credibility collapse during a DS interview if surfaced (e.g., "your survivorship-corrected number is what?"). Recoverable but expensive.
- **MEDIUM** — Degrades user experience or rigor but doesn't sink the project.

---

## Critical Pitfalls

### Pitfall 1: SEBI Investment-Advice / RA Boundary Violation

**Surface:** Honesty / regulatory.

**What goes wrong:**
DRHPLens output crosses from "informational analysis" into de-facto investment advice or research-analyst output, triggering SEBI's Investment Adviser (RIA) and/or Research Analyst (RA) regulations. The line is crossed by:

- Producing a "subscribe / avoid" verdict, even softly ("looks attractive", "we'd lean positive")
- Producing a personalized recommendation (model asks "what's your risk profile" and changes the answer)
- Publishing a forecasted listing-day return *without* prominent uncertainty + non-advice framing
- Using language SEBI flags as advisory: "buy", "subscribe", "target price", "fair value vs current price"
- Charging fees, even nominally, for the analysis

**Why it happens:**
LLMs default to confident, verdict-shaped language. "Producing a number" feels neutral to an engineer but reads as a recommendation to a regulator and to the user. The boundary is *behavioral* (does it function as advice?), not just linguistic.

**Warning signs (early detection):**
- Output contains words: "buy", "sell", "subscribe", "avoid", "target", "fair value", "undervalued", "overvalued", "recommend"
- A friend reading the output says "so should I apply?" and the answer feels like yes/no
- Forecast outputs a point estimate without an interval, or an interval without "this is not advice"
- Onboarding asks risk tolerance, age, income, or portfolio (these are RIA-triggering fields)
- No SEBI disclaimer visible above the fold

**Prevention (specific):**
1. **Hard-coded language guard rails** in the agent system prompt: a refusal/rewrite layer that scrubs banned tokens (`buy`, `sell`, `subscribe`, `avoid`, `recommend`, `target price`, `fair value`) before emitting.
2. **Disclaimer placement contract**: every page, every export, every shareable link carries "Informational and educational only. Not investment advice. Not a SEBI-registered Research Analyst or Investment Adviser." — minimum 10pt font per SEBI's 2025 RA guideline analogue.
3. **No personalization**: do not ask risk profile, age, capital. Same output for every user.
4. **AI-usage disclosure** mirroring the SEBI Jan-2025 circular: state that AI/LLMs are used, what they do, and that outputs may contain errors.
5. **Forecast framing**: always emit a *range* with a confidence level, and always pair it with the historical hit-rate of that interval ("intervals like this have contained the actual return X% of the time on backtest").
6. **No fees, no signup-walled-advice, no chat history that learns the user's portfolio** in v1.
7. **Legal review checkpoint** before public deployment.

**Phase to address:** Phase 0 / Foundation (compliance posture is a design constraint, not a layer added later). Re-verified at launch phase.

**Severity:** CRITICAL.

---

### Pitfall 2: Hallucinated Numbers in a Financial Product

**Surface:** RAG honesty / faithfulness.

**What goes wrong:**
The LLM fabricates a number (revenue, RPT amount, debt, promoter holding) that does not appear in the DRHP, or appears but in a different context (e.g., FY22 vs FY23). User reads it as fact. In finance, a hallucinated number is uniquely dangerous: it can move a subscription decision, and the user has no way to spot it because they're using DRHPLens *precisely because* they don't read the prospectus.

**Why it happens:**
- LLM "smooths" missing data with plausible-sounding numbers
- Citation drift: the LLM cites page 142 while the number actually came from its prior, not page 142
- Retrieval returned an adjacent table (e.g., "Restated Standalone" vs "Restated Consolidated") and the LLM didn't distinguish
- Year ambiguity: DRHPs show H1FY24 + FY23 + FY22 + FY21 side-by-side; the model picks the wrong column

**Warning signs:**
- Spot-checks fail: open the DRHP at the cited page, the number isn't there
- Same query at different temperatures returns different numbers
- Numerical RAGAS faithfulness < 0.9 on a numeric-only eval set
- The model cites a section title that doesn't exist in that DRHP
- Numbers reported without units or fiscal-year tags

**Prevention:**
1. **Numbers-only eval set**: 50+ manually verified Q-A pairs that ask for specific numbers; track faithfulness on this subset separately from prose questions. Gate releases on this metric.
2. **Two-stage answer protocol**: (a) retrieve and extract structured candidates (page, table, row, column, value, unit, fiscal_year); (b) LLM generates prose *only* by referencing the structured object. No free-floating numbers in generations.
3. **Forbid prose-only number emission**: every numeric claim in output must carry `(₹X cr, Source: DRHP p.142, Restated Consolidated, FY23)`. Strip generations that emit naked numbers.
4. **Verify-on-emit**: after generation, regex-extract all numerical claims, re-retrieve their cited spans, and run a faithfulness check (NLI or LLM-judge) per-claim. Fail-closed on mismatch.
5. **Table-aware chunking**: chunks that contain tables preserve column/row headers and fiscal-year banners. Never split a financial table mid-row.
6. **Page-level retrieval as a fallback** for financial-statement queries (research shows page-level retrieval beats chunk-level for long-doc financial QA).

**Phase to address:** RAG-pipeline phase. Pre-launch gate: numeric faithfulness ≥ 0.95.

**Severity:** CRITICAL.

---

### Pitfall 3: Survivorship Bias in Historical IPO Dataset

**Surface:** Listing-day forecasting.

**What goes wrong:**
The historical IPO dataset is built from currently-listed or easy-to-fetch tickers, which silently drops:

- IPOs that were **withdrawn** after DRHP filing
- IPOs whose issuers were **acquired / merged / delisted** post-listing
- IPOs whose tickers **changed** (name change, corporate action) and the old ticker is dead
- IPOs that flopped so badly the symbol no longer resolves in yfinance / NSE bhavcopy

Result: the historical "listing-day return" distribution is over-optimistic. Research on Indian small-caps shows backtests using only current index members overstate performance by ~23%; the same dynamic distorts IPO datasets.

**Why it happens:**
- "Current NSE listings" is the easy SQL query; "all NSE listings since 2010 including dead ones" is hard
- yfinance returns 404 / "No price data" for delisted symbols, and the pipeline silently filters them
- Bhavcopy archives exist but require painful ticker-mapping across name changes

**Warning signs:**
- Your IPO dataset has N matches to NSE's IPO list but N is suspiciously close to the count of *currently listed* companies
- Listing-day return distribution shows median > +10% (the published Indian-IPO median is ~7%, and that's already optimistic)
- No row with `status = withdrawn` or `status = delisted_post_listing`
- Cannot answer the question "how many IPOs from 2010–2020 are no longer tradeable today?"

**Prevention:**
1. **Build the universe from issuer-side data, not exchange-side data**: source from SEBI's offer-document list (DRHP filings) and NSE/BSE IPO history pages, *then* match to price data — not the reverse.
2. **Explicit `status` column** per IPO: `withdrawn`, `listed_alive`, `delisted`, `merged`, `name_changed`. Report the breakdown.
3. **Use historical ticker maps**: NSE publishes corporate-action / symbol-change history; ingest it.
4. **Replace-with-NaN, not drop**: when price data is missing, keep the row with NaN listing-day return and report separately.
5. **Compare against a published benchmark**: if your median listing-gain differs materially from published academic numbers (~7% median over a long period), assume survivorship until proven otherwise.
6. **Report the survivorship-adjusted vs naive distribution** in the methodology section — this is a DS-credibility *gain*, not a loss.

**Phase to address:** Data-ingestion / historical-IPO-dataset phase. Re-verified at modeling phase.

**Severity:** CRITICAL.

---

### Pitfall 4: Lookahead Bias from GMP / Subscription / Post-Issue Features

**Surface:** Listing-day forecasting.

**What goes wrong:**
The forecasting model trains on features that would not have been available at the moment of prediction. The biggest offenders in Indian IPO forecasting:

- **Subscription numbers (final QIB/HNI/Retail multiples)** — only known on Day 3 of the issue close, *after* the user's apply/no-apply decision
- **GMP at close** — same problem, plus GMP is self-reported dealer estimates with no audit
- **Anchor allocation %** — known T-1 of issue open
- **Issue-price band finalisation** — known only T-2 of issue open
- **Index level at listing** — obviously post-fact

If you train on the "final subscription" feature and evaluate listing-day return, you'll get a beautiful R², publish it on your portfolio, and at a DS interview be asked "when was that feature observable?" and the project collapses.

**Why it happens:**
- The data is easy to find post-hoc on aggregator sites
- It boosts metrics dramatically (subscription is essentially a leaked label)
- The temporal ordering of Indian IPO disclosures is not obvious to non-domain folks

**Warning signs:**
- Listing-day return model has R² > 0.5 — implausible for IPO returns; suspect leakage
- Top SHAP feature is `total_subscription_x` or `gmp_at_close`
- Features include any datum dated *after* the user's intended decision point
- No `feature_available_at` timestamp column

**Prevention:**
1. **Define the prediction timestamp explicitly**: "We predict listing-day return as of the moment the retail investor must decide whether to apply, i.e. issue open T0." Every feature has a `available_at` timestamp; reject any feature where `available_at > T0`.
2. **Two model variants, clearly labeled**:
   - `pre_apply`: only T0-available features (price band, anchor list, sector, financials, peer multiples, market regime indicators)
   - `post_close`: includes subscription/GMP-at-close; presented only as "what would happen if we knew this" — never as the production model
3. **Backtest must use point-in-time data**: do not use a final cleaned panel; reconstruct what was knowable on day-T for each historical IPO.
4. **Baseline model must beat naïve**: a "median listing gain in last 12 IPOs" baseline must be reported. If the ML model doesn't beat it, say so.
5. **Hold out by time, not random**: walk-forward / expanding-window evaluation. No random k-fold across years.

**Phase to address:** Modeling phase (data-leakage audit before any model is reported).

**Severity:** CRITICAL.

---

### Pitfall 5: Citation Drift / Wrong-Page Citations

**Surface:** RAG honesty.

**What goes wrong:**
The model cites "DRHP page 142" but the claim actually came from page 138 (or from the model's prior). User clicks the citation, sees an unrelated section, and the project's whole "honest, cited" value prop collapses on a single screenshot.

**Why it happens:**
- Chunk metadata carries the page of the *first* token of the chunk, but the relevant span is later
- LLM "rounds" page references when uncertain
- OCR-derived page numbers drift from PDF page numbers (DRHPs have Roman-numeral front matter + Arabic pagination)
- Multi-chunk retrieval; LLM cites the closest page rather than the actual source

**Warning signs:**
- Spot-checks: random sample 20 answers, click each citation, count how many land on the claimed content
- Page numbers in output are always round (every cite ends in 0 or 5)
- Citation accuracy < 0.95 on a manual audit
- LLM cites pages that don't exist in that DRHP

**Prevention:**
1. **Span-level citations, not page-level**: store start/end character offsets per chunk and surface a clickable highlight, not just a page number.
2. **Two-pagination scheme**: store both the PDF page index (0-indexed) and the printed-page number (which restarts in DRHPs after the front matter). Surface both, or always the printed one.
3. **Citation as structured field, not prose**: the LLM does not write `(p. 142)`; it emits a `claim_id` and the renderer attaches the citation from the retrieval object.
4. **Click-through audit eval**: in the eval harness, simulate a "user clicked citation" and verify the highlighted span contains the claim string (substring or NLI match).
5. **Reject ungrounded answers**: if a generated claim cannot be tied back to a retrieved chunk via an embedding similarity threshold, refuse and say "couldn't find this in the DRHP."

**Phase to address:** RAG-pipeline phase.

**Severity:** CRITICAL.

---

## High-Severity Pitfalls

### Pitfall 6: Regime-Shift Blindness in Forecasting

**Surface:** Listing-day forecasting.

**What goes wrong:**
Indian IPO regimes are *strongly* non-stationary. 2021 was a euphoric bull market with very different listing-day behavior than 2018 (volatility), 2023 (winter), or 2024–2025 (selective). Training on 2010–2024 as a single pooled sample produces a model that's average-of-regimes — wrong in every regime.

**Why it happens:**
- The standard ML reflex is to "use more data" by pooling years
- Regime labels are not in the raw data; you have to construct them
- Walk-forward backtests reveal regime collapse, but k-fold hides it

**Warning signs:**
- Model's residuals are autocorrelated by listing date
- Backtest by year shows wildly different RMSE across years
- Feature importance changes drastically across walk-forward folds
- Model is highly confident in regimes it has never seen (e.g., trained mostly on 2017–2022, evaluated in 2024)

**Prevention:**
1. **Regime indicator features**: include NIFTY trailing 6M return, India VIX, IPO-pipeline-density (number of IPOs in trailing 90 days), DII/FII net flows.
2. **Walk-forward evaluation with explicit per-year reporting** — not just aggregate.
3. **Conformal prediction intervals** (MAPIE / conformal regression) instead of parametric intervals — gives distribution-free coverage guarantees that adapt as the regime changes.
4. **Out-of-sample on the most-recent regime**: hold out the last 12 months as a final-test set, no peeking.
5. **Surface regime uncertainty in the UI**: "current regime is `selective` (NIFTY 6M return = +3%, VIX = 14). Historical accuracy in this regime: …"

**Phase to address:** Modeling phase + evaluation phase.

**Severity:** HIGH.

---

### Pitfall 7: Small-N Sector Slices

**Surface:** Listing-day forecasting.

**What goes wrong:**
Some sectors (defence, EV, fintech-NBFC, specialty chemicals) may have only 5–15 mainboard IPOs in the dataset. Per-sector models or per-sector calibrations will be wildly overfit. Headline "we account for sector" looks rigorous but is statistically empty for half the sectors.

**Why it happens:**
- Sector is a natural feature to add
- Sector-stratified evaluation looks more rigorous
- People forget to count N per sector before modeling

**Warning signs:**
- A per-sector coefficient has wider confidence interval than the coefficient itself
- "Sector = X" prediction at inference time relies on a sector the model saw < 10 times
- Per-sector RMSE varies by 10× across sectors

**Prevention:**
1. **Report N per sector** in the methodology page. Sectors with N < 30 get pooled into "Other" or use a hierarchical shrinkage model.
2. **Hierarchical / partial-pooling model** (e.g., Bayesian mixed-effects with `sector` as a random effect) so small-N sectors borrow strength from the mean.
3. **Refuse to forecast** for IPOs in sectors with no historical comparable IPOs; surface that as a *feature* of the honest framing.
4. **Show per-sector calibration**: a sector-stratified calibration plot.

**Phase to address:** Modeling phase.

**Severity:** HIGH.

---

### Pitfall 8: Agent Tool-Call Infinite Loop / Hard Crash

**Surface:** Agentic orchestration.

**What goes wrong:**
LangGraph (or similar) agent bounces between agent-node and tool-node until it hits `recursion_limit` (default 25) and throws a hard exception. In the demo, this is "the page just hangs and then errors." Common triggers:

- LLM hallucinates a tool argument; tool returns 400; LLM "fixes" by sending the same malformed query
- Tool returns no result; LLM retries with the same query
- Two tools' outputs depend on each other in a cycle the LLM can't break

**Why it happens:**
- LLMs don't natively learn from tool errors mid-trace
- No semantic deduplication of tool calls
- No supervisor / critic node

**Warning signs:**
- Latency suddenly jumps to 30s+ on certain queries
- Logs show the same tool called 5+ times with identical args
- `GraphRecursionError` in error tracking
- User reports "it just spun"

**Prevention:**
1. **Step counter (TTL) in graph state**: hard cap on agent iterations, with graceful degradation (return partial result + "I couldn't fully answer") rather than a 500.
2. **Semantic cache of tool calls within a trace**: if `(tool_name, args_hash)` already executed in this run, inject a "you already tried this exact call, it returned X" message and force a different path.
3. **Strict tool input schemas** (Pydantic / JSON schema): reject malformed args before the tool runs and feed the schema error back to the LLM.
4. **Supervisor node** with smaller model that audits trajectory every N steps and can force-stop.
5. **Tool-call observability**: log every (tool, args, result) per session; export traces (LangSmith / OpenTelemetry).
6. **Eval set of "weird user queries"** to stress agent control flow before launch.

**Phase to address:** Agent-orchestration phase.

**Severity:** HIGH.

---

### Pitfall 9: Naive Baselines Beat the Model — Silently

**Surface:** DS portfolio framing.

**What goes wrong:**
The ML listing-day model has RMSE 18%. Sounds reasonable. Then in an interview: "what's the RMSE of always predicting the trailing-3-month median?" Answer: 17.5%. The project's modeling contribution is negative.

**Why it happens:**
- Engineers compare ML model A to ML model B, not to a constant
- Baseline construction is "boring" and gets skipped
- Listing-day returns have huge variance; almost everything looks ok

**Warning signs:**
- No baseline reported in the README
- "Baseline" is another ML model, not a constant or trivial heuristic
- The model's improvement over baseline is < 5% relative and not statistically tested

**Prevention:**
1. **Mandatory baselines** (report all four):
   - Predict zero (no listing pop)
   - Predict global median
   - Predict trailing-12-IPO median
   - Predict sector-mean (last N in sector)
2. **Statistical significance test** on the improvement (Diebold-Mariano or bootstrap CI on RMSE diff).
3. **If the ML model fails to beat baseline**, the portfolio piece *says so* and frames the project around honest evaluation rather than predictive performance. This is actually a stronger DS signal than fake gains.

**Phase to address:** Modeling phase + portfolio-writeup phase.

**Severity:** HIGH.

---

### Pitfall 10: Evaluation Theater (Numbers Without Interpretation)

**Surface:** DS portfolio framing.

**What goes wrong:**
README shows: `RAGAS Faithfulness: 0.87, Context Recall: 0.79, Listing-day RMSE: 18.2%, Calibration: 0.92.` No one knows what those numbers mean, whether they're good, or what the failures look like. Interviewer reads them, asks "what does 0.87 faithfulness *miss*?", and the project owner can't answer because they never inspected the failures.

**Why it happens:**
- Metrics are easier to compute than to interpret
- RAGAS / standard benchmarks are LLM-as-judge graders — they can be wrong, and "0.87" gives false certainty
- Interpretation is unpaid labor; metric tables are visible

**Warning signs:**
- README lists numbers without a "what these mean" paragraph
- No qualitative failure-mode section
- No comparison to a literature/industry benchmark for "what's reasonable"
- Can't answer "show me a query where faithfulness was rated 1.0 but the answer was actually wrong"

**Prevention:**
1. **Every headline metric has a paragraph** explaining: (a) what it measures, (b) what the literature/sane range is, (c) what failures it doesn't catch, (d) sample failure case.
2. **Failure gallery**: a section of the writeup that shows 5–10 representative failures with commentary.
3. **Human-judged spot-checks** alongside LLM-judge metrics (LLM-as-judge has known blind spots; report agreement rate).
4. **Per-question-type breakdown**: numeric questions, definitional questions, multi-hop questions — separate scores.
5. **Methodology page** that walks through one full example end-to-end.

**Phase to address:** Evaluation phase + portfolio-writeup phase.

**Severity:** HIGH.

---

### Pitfall 11: All-LLM-Glue, No Real Modeling

**Surface:** DS portfolio framing.

**What goes wrong:**
The project is, in practice, "LangChain + GPT-4 + a PDF parser." There's no model the project owner trained, tuned, or evaluated rigorously. For an ML Engineer role this is fine; for a Data Scientist role (DRHPLens's stated target) this is fatal — DS interviewers want to see modeling judgment, not API composition.

**Why it happens:**
- LLM APIs make 80% of any RAG demo "work"
- Real modeling (forecasting, NLP extraction, embedding fine-tuning) is hard and slow
- Scope creep on the agent eats time the forecasting model needed

**Warning signs:**
- The forecasting "model" is `mean(last_n_sector_returns)`
- No model card, no hyperparameter discussion, no cross-validation report
- The only ML decision was "which embedding model to use"
- Repo has no `models/` or `notebooks/training/` with substantive content

**Prevention:**
1. **Time-budget contract**: at least 35–40% of build time goes to *non-LLM* modeling work (forecasting model, calibration, NLP extraction evaluation).
2. **At least two non-LLM modeling artefacts** visible: (a) the listing-day forecaster with proper train/val/test discipline, (b) a fine-tuned or evaluated extractor for one structured field (e.g., RPT extraction, promoter-pledge detection).
3. **Model card** for the forecaster: features, training data window, evaluation protocol, calibration, known failure modes.
4. **DS-flavored writeup**: feature engineering rationale, ablations, residual analysis, calibration plots, conformal intervals — these are the artefacts a DS interviewer will look for.
5. **Cut agent scope before cutting modeling scope.**

**Phase to address:** Roadmap phase (sequencing) + modeling phase (deliverables).

**Severity:** HIGH.

---

### Pitfall 12: Risk-Factor Boilerplate Inflates Extraction Metrics

**Surface:** NLP over DRHPs.

**What goes wrong:**
DRHP risk-factor sections share massive boilerplate across IPOs ("Our business is dependent on macroeconomic conditions in India…"). An extractor that "finds risks" with 95% recall might just be reproducing template language. Real-signal risks (issuer-specific litigation, promoter pledging, going-concern flags) get lost in template noise. To a Data Scientist evaluator, "extracted 47 risk factors" with no deduplication is a smell.

**Why it happens:**
- DRHP risk-factor sections often share 60–80% of phrasing across issuers (drafted by the same merchant bankers)
- Standard NER / extraction metrics treat each match equally
- Generic risks are easier to extract than specific ones

**Warning signs:**
- Top "extracted risks" across multiple IPOs are near-identical strings
- Extractor recall is high but inter-IPO overlap of extracted risks is > 50%
- No "issuer-specific" vs "generic" classification on outputs
- Demo shows "we found these 30 risks" without ranking by specificity

**Prevention:**
1. **Cross-IPO IDF**: weight extracted risk statements by inverse-document-frequency across a corpus of DRHPs. High-IDF = issuer-specific = surface; low-IDF = boilerplate = collapse into a "standard market risks" rollup.
2. **Two-bucket output**: `issuer_specific_risks` (the differentiating ones) vs `industry_standard_risks` (the boilerplate).
3. **Evaluate on issuer-specific recall**, not gross recall — have an annotator label the top N risks per IPO as specific vs boilerplate and report metrics on the specific subset.
4. **Surface diff vs peers**: "this DRHP's risks that *don't* appear in 80%+ of comparable IPOs."

**Phase to address:** NLP-extraction phase.

**Severity:** HIGH.

---

### Pitfall 13: Embedding Mismatch on Indian-English / Domain Vocabulary

**Surface:** RAG / NLP.

**What goes wrong:**
General-purpose embeddings (OpenAI `text-embedding-3-*`, BGE base, etc.) don't have great representations for:

- Indian-English financial terms (`promoter`, `promoter group`, `HUF`, `KMP`, `lakh`, `crore`, `RPT`, `bonafide`, `consortium`)
- Indian regulatory acronyms (`SEBI`, `RBI`, `MCA`, `FEMA`, `LODR`)
- Entity types specific to India (Hindu Undivided Family, Limited Liability Partnership variants)

Retrieval misses, especially on cross-referenced sections.

**Why it happens:**
- Defaulting to OpenAI / generic embeddings is the path of least resistance
- These terms are rare in English web crawls relative to US-finance terms
- Hard to tell embedding quality is the bottleneck vs prompt / chunk quality

**Warning signs:**
- Retrieval recall@k on Indian-finance-specific queries < on generic queries
- "Find related-party transactions" returns the RPT section sometimes but misses the cross-referenced annexure
- The system finds a section by exact-word match but misses paraphrases ("promoter family" vs "promoter group")

**Prevention:**
1. **Evaluate at least two embeddings**: one general (e.g., `text-embedding-3-large`) and one Indian/finance-friendly (e.g., a multilingual or finance-tuned model). Measure recall@10 on a labeled set.
2. **Hybrid retrieval (BM25 + vector)**: BM25 catches the acronym-heavy queries; vector catches paraphrase. Reciprocal-rank-fusion (RRF) or weighted blend.
3. **Glossary / synonym expansion**: a small Indian-finance synonym dictionary applied at query time (`promoter family` → `promoter group | promoter and promoter group`).
4. **Cross-encoder reranker** on top-K to recover precision after broad retrieval.
5. **Domain term coverage test**: a fixed list of Indian-finance terms with known DRHP locations; assert retrieval finds them.

**Phase to address:** RAG-pipeline phase.

**Severity:** HIGH (because it silently degrades the user-facing product).

---

## Medium-Severity Pitfalls

### Pitfall 14: Brittle DRHP-Source Ingestion

**Surface:** Indian-financial-data quirks.

**What goes wrong:**
SEBI's public-issues page changes URL patterns. BSE/NSE move PDFs. DRHP file naming has no convention (issuer name in CamelCase, dates in different formats, "Final" vs "Updated" vs no marker). Pipeline silently picks up the wrong file or misses new IPOs.

**Why it happens:**
- Indian regulatory sites are notoriously inconsistent and redesigned without notice
- No EDGAR-equivalent firehose
- Aggregator sites (chittorgarh, ipocentral, investorgain) are convenient but undocumented

**Warning signs:**
- Pipeline runs but no new IPOs appear for a week even when there should be
- DRHP version drift: ingested file is the *draft* RHP, not the final RHP, but treated as the latter
- File hashes change without obvious reason (re-uploaded with cosmetic edits)

**Prevention:**
1. **Multi-source redundancy**: SEBI offer-documents page + NSE/BSE IPO history + at least one aggregator, with cross-checks.
2. **Version tracking**: store SHA-256 of every DRHP/RHP ingested with a `version_seen_at` timestamp; alert on silent re-uploads.
3. **DRHP vs RHP discrimination**: detect from the document title page and tag clearly; the RHP price band is materially different from the DRHP.
4. **Manual-fallback queue**: when scraping fails, alert and allow manual upload of a single DRHP — don't let one source break the whole product.
5. **Monitoring**: weekly job that lists "IPOs that NSE/BSE shows but we don't have a DRHP for" — investigate the gap.

**Phase to address:** Data-ingestion phase.

**Severity:** MEDIUM (annoying, recoverable).

---

### Pitfall 15: yfinance / NSE Price Data Quality

**Surface:** Indian-financial-data quirks.

**What goes wrong:**
`yfinance` has documented issues with Indian tickers — false "delisted" errors on active stocks, missing timezone data, intermittent fetch failures for `.NS` / `.BO` suffixes. Listing-day prices may be missing, splits/bonuses may not be back-adjusted, dividend adjustments may be inconsistent.

**Why it happens:**
- yfinance is unofficial Yahoo Finance scraping; Yahoo's coverage of Indian markets is second-tier
- Splits and bonuses are common in India and not always reflected promptly
- Multi-listed stocks (NSE + BSE) can return different histories under `.NS` vs `.BO`

**Warning signs:**
- "No price data" for stocks you know are trading
- Listing-day OHLCV missing for some IPOs
- Adjusted-close jumps without an obvious corporate action
- Same ticker returns different histories on different days

**Prevention:**
1. **Primary source = NSE/BSE bhavcopy archives** (daily CSV downloads), not yfinance. yfinance is a convenience layer for recent data only.
2. **Corporate-action ledger**: ingest NSE's corporate-actions page; verify all splits/bonuses are reflected in adjusted prices.
3. **Per-IPO listing-day price audit**: manually verify a sample of listing-day prices against NSE archives during dataset construction.
4. **Listing-day return defined precisely**: `(listing_day_close - issue_price) / issue_price`, with `listing_day_close` = close on the first NSE trading day. Document this; don't use a vague "first day return."
5. **Both-exchange reconciliation**: fetch `.NS` and `.BO` separately for cross-listed stocks; flag mismatches.

**Phase to address:** Data-ingestion phase.

**Severity:** MEDIUM.

---

### Pitfall 16: Screener.in / Aggregator ToS and Rate Limits

**Surface:** Indian-financial-data quirks.

**What goes wrong:**
Project depends on scraping screener.in or other aggregators for peer fundamentals. Aggregator changes layout or rate-limits the IP; demo breaks during the interview. Also: aggregator ToS may prohibit scraping; legally fragile.

**Why it happens:**
- Aggregators are the easy way to get cleaned peer fundamentals
- No formal API; defaults to HTML scraping
- ToS often forbids redistribution even when scraping is technically possible

**Warning signs:**
- 429s in the scraper logs
- Demo fails when run from a fresh IP / cloud machine
- ToS review never happened

**Prevention:**
1. **Cache aggressively**: scrape once, store locally, refresh on a slow schedule (weekly/monthly for peer fundamentals).
2. **Polite scraping**: respect robots.txt, throttle to ≥ 2s between requests, set a real UA, contact form for permission if scaling up.
3. **Prefer first-party sources where possible**: BSE/NSE company filings, MCA/ROC filings, company IR pages.
4. **Don't redistribute scraped raw data**: store derived/aggregated representations in your product; legally cleaner.
5. **Plan-B source list**: at least two paths to peer fundamentals; if one breaks, switch.

**Phase to address:** Data-ingestion phase + legal-review checkpoint.

**Severity:** MEDIUM (escalates to HIGH if demo breaks during a high-stakes review).

---

### Pitfall 17: Calibration Theatre (Reporting Calibration Without Coverage)

**Surface:** Listing-day forecasting.

**What goes wrong:**
Model reports a "95% prediction interval" that empirically contains the true return only 60% of the time. The interval looks rigorous but is materially miscalibrated. Worse than no interval, because users trust it.

**Why it happens:**
- Parametric intervals (Gaussian) assume residual normality, which fails for IPO returns (heavy-tailed, often bimodal)
- No empirical coverage check
- "Calibration plot" reported but only on training data

**Warning signs:**
- Coverage of 95% PI on test set is < 90% or > 99%
- Residuals are visibly heavy-tailed or skewed in a Q-Q plot
- No `coverage_at_95` metric reported
- Intervals are the same width regardless of how unusual the query IPO is

**Prevention:**
1. **Conformal prediction** (split-conformal or jackknife+) for distribution-free coverage. Report empirical coverage on held-out and rolling-window test sets.
2. **Adaptive intervals**: width should depend on the IPO's similarity to historical comparables, not be constant.
3. **Report coverage as a first-class metric**, not just RMSE.
4. **Calibration plot on test set**, with N-binned reliability bars and 95% CI on each bin.
5. **Communicate the uncertainty source**: distinguish epistemic (small N for this sector) from aleatoric (markets are random) in the UI.

**Phase to address:** Modeling phase + evaluation phase.

**Severity:** MEDIUM (HIGH if surfaced in interview).

---

### Pitfall 18: Agent "Answers Without Retrieving"

**Surface:** Agentic orchestration.

**What goes wrong:**
The agent skips the retrieval tool for an "easy" question and answers from prior. The answer is plausible but not grounded in the actual DRHP. User can't tell.

**Why it happens:**
- Strong LLMs answer DRHP-style questions from training prior alone
- No hard contract that retrieval *must* be called
- Cost / latency optimisation tempts skipping retrieval on "obvious" questions

**Warning signs:**
- Agent traces show zero tool calls for some user questions
- Answers contain no citations
- Numbers appear in output without source attribution

**Prevention:**
1. **Retrieval-mandatory contract**: any answer about a specific IPO *must* include at least one DRHP-cited claim; if retrieval returned no relevant chunks, the agent must say so.
2. **Output-schema enforcement**: the answer schema requires `citations: [{...}]` and is rejected by the renderer if empty (for IPO-specific queries).
3. **Trace audit eval**: random sample 50 sessions/week; assert retrieval was called and citations resolve.
4. **No "general knowledge" mode**: if a query is too generic to require DRHP retrieval, the agent should redirect to a glossary, not answer from prior.

**Phase to address:** Agent-orchestration phase + evaluation phase.

**Severity:** MEDIUM.

---

### Pitfall 19: Demo-Day Fragility

**Surface:** DS portfolio framing + deployment.

**What goes wrong:**
The interviewer opens the live URL; cold-start latency is 40s; OpenAI rate-limits hit; a single DRHP costs $3 to process and the demo runs out of budget mid-call.

**Why it happens:**
- Free-tier infra has cold starts
- LLM costs scale with PDF length; DRHPs are 400 pages
- No precomputed corpus; everything runs at query time

**Warning signs:**
- p95 latency > 15s
- Per-query LLM cost > $0.20
- Budget burn rate would exceed free-tier limits at 100 queries/day
- App fails health check after periods of idle

**Prevention:**
1. **Pre-index a fixed corpus** of ~20–50 mainboard IPOs from the last 2 years. Don't ingest at query time.
2. **Cache LLM responses** per (question, IPO, model_version) — same query returns the cached answer.
3. **Cheap-tier model for routing/extraction**, expensive model only for final answer synthesis.
4. **Warm-keep the app** with a tiny cron pinger (free uptime monitors).
5. **Offline demo path**: a 2-minute screen-recording walkthrough on the README, so the project survives a demo outage.
6. **Cost budgets per IPO** monitored and surfaced ("indexing this DRHP costs ~$X").

**Phase to address:** Deployment phase.

**Severity:** MEDIUM (becomes HIGH on demo day).

---

### Pitfall 20: Scope Creep — V1 Never Ships

**Surface:** DS portfolio framing.

**What goes wrong:**
The project keeps growing: "let me also add ESG analysis, then peer multiples for unlisted comps, then a chat interface, then…". Six months in, nothing is end-to-end working. The single biggest failure mode of ambitious solo DS portfolio projects.

**Why it happens:**
- Each new feature is more fun than polishing the boring parts (evals, docs, deployment)
- The DRHPLens domain is genuinely rich; there's always one more thing
- No external deadline forcing v1

**Warning signs:**
- More than 3 weeks without a deployable end-to-end demo
- The README's "what's done" list grows but the "ships to users" date keeps slipping
- New features are being added while old features lack tests/eval
- Forecasting model is still "in notebook" form weeks after the RAG pipeline shipped

**Prevention:**
1. **Slice end-to-end first** — even an embarrassing v0 — before going deep on any layer. Define "end-to-end" precisely: user enters an IPO name → gets a cited summary + a calibrated listing-day range.
2. **Phase gates with explicit ship criteria**, enforced even if a phase feels incomplete.
3. **Feature freeze 3 weeks before "portfolio-ready" date.**
4. **De-scope list owned upfront**: features that explicitly will not be in v1 (per PROJECT.md already does this — good).
5. **Bias toward "make the existing thing more rigorous" over "add new thing."**

**Phase to address:** Roadmap phase (sequencing and gates).

**Severity:** MEDIUM (becomes HIGH because it silently kills portfolio projects).

---

### Pitfall 21: Bad UX — User Reads Honest Output as Advice Anyway

**Surface:** Honesty / not-advice framing.

**What goes wrong:**
The model output is correctly hedged, but the UI emphasises the forecast number in big type at the top of the page. User screenshots the number, ignores the interval and the disclaimer, and treats it as a recommendation. Now you have a regulatory + reputational issue.

**Why it happens:**
- Visual hierarchy is doing the opposite of what the words say
- "Forecast = 12%" is more screenshot-friendly than "calibrated 80% interval = [-8%, +24%]"
- Disclaimers in small grey text below the fold

**Warning signs:**
- The most prominent element on a result page is a point estimate, not an interval
- The disclaimer is below the fold
- Sharing-cards / OG-image preview shows the number without the interval
- User testing: 3/5 users describe the output as "DRHPLens says I should subscribe"

**Prevention:**
1. **Visual prominence to the interval, not the point**: show `[-8%, +24%, 80% confident]` as the main visual; if a point estimate appears at all, it's small and labeled "midpoint."
2. **Disclaimer above the fold**, top of every result.
3. **Sharing cards explicitly include the disclaimer** in the OG image.
4. **User-testing protocol**: ask 5 users "what would you do based on this?" — if any say "subscribe / not subscribe", redesign.
5. **No green/red colour coding** of the forecast (this reads as buy/sell).

**Phase to address:** UI/UX phase + launch-readiness phase.

**Severity:** MEDIUM.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Ingest current-listed-only IPOs (skip delisted/withdrawn) | Faster dataset build; everything has prices | Survivorship-biased forecasts; portfolio-killer in interview | NEVER for v1 — survivorship is too core to the value prop |
| Use a single embedding model + chunker without ablation | Faster RAG pipeline ship | Can't justify retrieval choice; no DS depth signal | Only for an internal v0; must do at least one ablation before portfolio-ready |
| Use GPT-4 for everything (no smaller-model routing) | Simplest agent code | Costs blow past free tier; demo can break | Acceptable in dev; replace with routing before launch |
| Skip the RHP-vs-DRHP version check | Faster ingest | Wrong price band → wrong analysis | NEVER — always tag document version |
| Inline LLM API keys in the deployed app | Faster to ship | Key leaks, blown budget, demo dies | NEVER — use server-side proxy from day 1 |
| Train forecaster on the full pooled 2010–2025 sample with k-fold | Higher reported R² | Regime-blind, inflated metrics | NEVER — walk-forward is mandatory |
| Use LLM-as-judge metrics only, no human spot-check | Cheap evaluation | LLM-judge blind spots accepted as truth | Acceptable in dev; must add human spot-check (≥50 examples) before portfolio-ready |
| Treat "RAGAS faithfulness = 0.85" as good without inspecting failures | Quick metric line in README | Evaluation theater; can't answer interview questions about failure modes | NEVER for portfolio purposes |
| Hard-code a list of IPOs instead of building the pipeline | Get to RAG layer faster | "Pipeline" claim in portfolio is fake | OK for v0 demo, but pipeline must exist before portfolio-ready |
| Skip the "is this query about IPO X or peers" routing | Simpler agent | Cross-contaminated retrieval | OK in v0; add intent classifier before launch |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SEBI offer-documents page | Hard-coded URL pattern that breaks on site redesign | Crawl from a stable index page; fall back to BSE/NSE; version-tag fetches |
| NSE / BSE corporate actions | Ignored; using only adjusted close from yfinance | Ingest NSE corporate-actions feed and verify splits/bonuses |
| `yfinance` (`.NS` / `.BO`) | Trusting it as primary price source | Use as convenience only; primary = NSE bhavcopy archives |
| Screener.in (peer fundamentals) | Scraping without caching / throttling | Cache once weekly, throttle, prefer first-party IR pages where possible |
| OpenAI / Anthropic APIs | No rate-limit / cost guard | Budget caps per session; circuit-breaker; cheap-model routing |
| LangChain / LangGraph | Default recursion limit = silent crash | Custom step-counter + supervisor + semantic dedup of tool calls |
| Vector DB (Chroma / pgvector / etc.) | No metadata filters; retrieving across all IPOs by default | Per-IPO namespacing; mandatory `ipo_id` filter on every query |
| PDF parser (Unstructured / PyMuPDF) | Trusting one parser for all DRHPs | Two parsers + diff; route to OCR for scanned tables |
| Aggregator IPO calendars (chittorgarh, investorgain) | Treating as authoritative | Cross-check against SEBI/NSE/BSE; ToS-aware caching |
| LLM JSON-mode tool calls | Schema-loose; LLM fills in plausible nonsense | Pydantic-validated schemas with field-level constraints; reject + retry |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Index DRHP at query time | First query for any new IPO = 60s+ latency | Pre-index a fixed corpus; background-index new IPOs | Immediately, on first user demo |
| No per-query LLM cost cap | Single user can run up $X in minutes | Per-session budget; rate-limit per IP; cheaper model for routing | When the demo URL gets shared on Twitter / r/IndiaInvestments |
| Re-running full eval suite on every commit | CI takes 20+ minutes; team stops running it | Tiered eval: fast subset on commit, full nightly | First week of intensive iteration |
| Vector DB without metadata filters | Retrieval slows as corpus grows; cross-IPO leaks | `ipo_id` and `section_type` as mandatory filters | At 20+ IPOs in corpus |
| Loading the full DRHP into LLM context "just in case" | Per-query cost balloons; latency rises; quality often *decreases* | Strict top-K chunks; longer context only when justified | Immediately |
| Synchronous DRHP-PDF download + parse in user request | 30s+ initial latency; timeouts | Background ingestion worker; user sees "indexing" state | First production user |

---

## Security / Compliance Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing scraped DRHP PDFs and serving them from your domain | Copyright complaints from issuers / SEBI; trademark issues | Link out to the original SEBI / exchange URL; don't host PDFs you don't own |
| Logging full user queries indefinitely without privacy notice | DPDP Act (India) exposure; portfolio-stage but still applies | Anonymise; explicit privacy notice; minimal retention |
| Letting users upload arbitrary PDFs and treating them as DRHPs | Adversarial inputs (prompt injection via PDF text), malicious PDFs | Trusted-source-only ingestion in v1; if user upload is allowed, sanitize + sandbox |
| LLM API keys in client-side code | Key theft, blown budget | Server-side proxy only; per-IP rate limits |
| No abuse/spam mitigation on a free public endpoint | Crawlers, abusers run up your costs | Rate-limit per IP; CAPTCHA on high-volume; circuit breaker on cost |
| Producing forecasts without the SEBI-style not-advice disclaimer | Regulatory exposure (see Pitfall 1) | Disclaimer enforced at render time, not just in prompt |
| Storing user PII (email, phone) without need | DPDP Act; portfolio overhead | Don't collect what you don't need; if collected, encrypt + minimise |
| Allowing arbitrary user-supplied queries into tool args | Prompt injection / SQL-like injection into peer-comparison queries | Validate tool args server-side; never let user text reach raw DB queries |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Big point-estimate forecast on top of the page | Reads as recommendation; disclaimer ignored | Lead with the interval + regime context; point estimate de-emphasised |
| Citations rendered as `(p.142)` plain text | User can't verify; trust assumption only | Clickable spans that open a highlighted PDF viewer at the exact location |
| "Subscribe" / "Avoid" colour cues (green/red) | Reads as advice regardless of words | Neutral palette; no buy/sell coding |
| Long verbose answers that bury the key finding | User doesn't read; misses the point | Structured output: Summary → Key Risks → Financial Snapshot → Peers → Listing-Day Range. TL;DR up top. |
| No way to ask follow-up questions on the same IPO | User has to re-type context | Session-scoped conversation per IPO |
| Forecast shown for IPOs with N<10 historical peers without flagging | User trusts a model with no data | Surface confidence-source: "based on only 4 historical comparables — interval is very wide" |
| Single forecast number with no decomposition | User can't critique or learn | Show the contributing factors (market regime, sector base rate, subscription proxy, valuation gap) |
| No "explain how you got this" affordance | Black box — DS-credibility loss | Methodology link in every answer; "see how" expandable per claim |
| Confusing DRHP vs RHP version to the user | User sees DRHP price band that's already obsolete | Tag visibly; prefer the latest filed version; show last-updated |
| Indian-finance jargon without glossary (RPT, KMP, HUF) | Retail user lost | Inline glossary tooltips |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces. To be run at each phase exit.

- [ ] **RAG pipeline**: Often missing per-claim citation verification — verify clicking a citation lands on the actual claim text in the PDF.
- [ ] **Listing-day forecaster**: Often missing baseline comparison and walk-forward backtest — verify there are at least 4 baselines reported and per-year RMSE.
- [ ] **Historical IPO dataset**: Often missing withdrawn / delisted IPOs — verify a non-trivial number of rows have `status != listed_alive`.
- [ ] **Evaluation harness**: Often missing failure gallery — verify there are ≥10 inspected failure cases with commentary.
- [ ] **Forecast intervals**: Often missing empirical coverage check — verify reported 80% PI contains the truth 75–85% of the time on test.
- [ ] **Citation system**: Often missing wrong-page audit — verify ≥95% of citations land on the actual claim text in a 50-query audit.
- [ ] **Agent orchestration**: Often missing TTL / loop guards — verify a deliberately broken tool call doesn't crash the app.
- [ ] **Compliance**: Often missing disclaimer on shared / OG-card previews — verify a shared link's preview image contains the disclaimer.
- [ ] **Numeric extraction**: Often missing fiscal-year disambiguation — verify all numerical claims carry a fiscal-year tag.
- [ ] **DRHP versioning**: Often missing DRHP-vs-RHP discrimination — verify each ingested file is tagged with its version.
- [ ] **NLP extractor**: Often missing boilerplate filter — verify top extracted risks across 5 IPOs are not near-identical.
- [ ] **Deployment**: Often missing cold-start handling — verify p95 latency on a cold app < 10s, and that the demo doesn't depend on caches that may not warm.
- [ ] **Methodology page**: Often missing on portfolio projects — verify there's a public page explaining the modeling, evaluation, and known limitations.
- [ ] **DS depth**: Often missing — verify there's at least one substantive non-LLM modeling artefact (forecaster with full discipline, or fine-tuned extractor).

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hallucinated numbers detected post-launch | HIGH | Pull product to "beta-only"; add per-claim verification; re-evaluate numeric faithfulness; only relaunch when ≥0.95 |
| Survivorship bias discovered in dataset | MEDIUM | Rebuild dataset from SEBI offer-doc list; rerun all forecast metrics; publish "naive vs survivorship-corrected" comparison as a methodology asset |
| Lookahead bias discovered in features | HIGH | Audit feature `available_at` timestamps; rerun walk-forward backtest; retract any prior performance claims |
| Citation drift discovered | MEDIUM | Move to span-level citations; click-through audit; gate release on ≥95% citation accuracy |
| Agent loop in production | LOW | Add TTL + semantic cache; graceful degradation; ship in hours |
| SEBI / regulatory ambiguity raised | HIGH | Pull forecasts and verdict-shaped language; legal review; relaunch as pure "summariser + uncertainty" if needed |
| Data source breaks (SEBI / NSE redesign) | MEDIUM | Switch to backup source; queue manual upload; restore within days |
| Model fails to beat baseline | LOW | Be honest about it in the writeup; pivot framing to "honest evaluation + RAG" rather than predictive performance |
| Demo URL down during interview | MEDIUM | Pre-recorded video walkthrough on README; local-run instructions; offline screenshots |
| Demo cost burns through budget | LOW | Per-session budget caps; cheaper model routing; cache aggressively |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls. Phase names are indicative; the roadmap may rename.

| Pitfall | Severity | Prevention Phase | Verification |
|---------|----------|------------------|--------------|
| 1. SEBI investment-advice boundary | CRITICAL | Foundation / compliance posture (Phase 0) | Disclaimer audit on every page; banned-token scrubber test passes; legal review checkpoint before launch |
| 2. Hallucinated numbers | CRITICAL | RAG pipeline + evaluation | Numeric-faithfulness ≥ 0.95 on 50-query eval set; per-claim verification active |
| 3. Survivorship bias | CRITICAL | Data-ingestion / historical-IPO dataset | `status` column present; withdrawn/delisted rows > 0; published vs internal median sanity-checked |
| 4. Lookahead bias | CRITICAL | Modeling | All features have `available_at`; walk-forward backtest only; no random k-fold reported |
| 5. Citation drift | CRITICAL | RAG pipeline | ≥95% citation accuracy on 50-query click-through audit |
| 6. Regime-shift blindness | HIGH | Modeling + evaluation | Walk-forward per-year RMSE reported; regime features included; conformal intervals |
| 7. Small-N sector slices | HIGH | Modeling | N-per-sector reported; sectors < 30 pooled or hierarchical model |
| 8. Agent infinite loops | HIGH | Agent orchestration | TTL + semantic cache + supervisor active; deliberately broken-tool test passes |
| 9. Naive baselines beat the model | HIGH | Modeling + portfolio writeup | At least 4 baselines reported with statistical significance test |
| 10. Evaluation theater | HIGH | Evaluation + portfolio writeup | Every headline metric has an interpretation paragraph + failure gallery |
| 11. All-LLM-glue / no real modeling | HIGH | Roadmap sequencing | ≥35% time on non-LLM modeling; model card + ablations exist |
| 12. Risk-factor boilerplate inflates metrics | HIGH | NLP extraction | IDF-weighted; issuer-specific vs boilerplate split; eval on specific-only |
| 13. Embedding mismatch on Indian-English | HIGH | RAG pipeline | At least 2 embeddings evaluated; hybrid retrieval; domain-term coverage test |
| 14. Brittle DRHP ingestion | MEDIUM | Data ingestion | Multi-source redundancy; SHA versioning; manual-fallback queue |
| 15. yfinance data quality | MEDIUM | Data ingestion | Bhavcopy as primary; corporate-actions ledger; listing-day price audit |
| 16. Aggregator ToS / rate limits | MEDIUM | Data ingestion + legal | Cache aggressively; throttle; Plan-B source list |
| 17. Calibration theatre | MEDIUM (HIGH if surfaced) | Modeling + evaluation | Empirical coverage on test set; calibration plot; conformal intervals |
| 18. Agent answers without retrieving | MEDIUM | Agent orchestration + evaluation | Retrieval-mandatory schema; trace audit eval passes |
| 19. Demo-day fragility | MEDIUM (HIGH on demo day) | Deployment | p95 latency < 10s cold; per-session budgets; offline demo video |
| 20. Scope creep / v1 never ships | MEDIUM (HIGH for project survival) | Roadmap sequencing | End-to-end v0 within first 3 weeks; phase gates with explicit ship criteria |
| 21. UX implies advice | MEDIUM | UI/UX + launch readiness | User-testing protocol; visual-hierarchy audit; OG-card disclaimer |

---

## Sources

- [Decomposing Retrieval Failures in RAG for Long-Document Financial Question Answering (arXiv)](https://arxiv.org/pdf/2602.17981) — page-level retrieval as a mitigation for chunk-level retrieval failures in long financial documents.
- [Empirical Evaluation of PDF Parsing and Chunking for Financial Question Answering with RAG (arXiv)](https://arxiv.org/abs/2604.12047) — PDF parsing pitfalls and chunking trade-offs for financial RAG.
- [Long-Context Isn't All You Need: How Retrieval & Chunking Impact Finance RAG (Snowflake Engineering)](https://www.snowflake.com/en/engineering-blog/impact-retrieval-chunking-finance-rag/) — chunking and retrieval impact on finance RAG quality.
- [FinSage: A Multi-aspect RAG System for Financial Filings QA (arXiv)](https://arxiv.org/pdf/2504.14493) — multi-aspect retrieval for financial filings.
- [Survivorship Bias in Emerging Market Small-Cap Indices: Evidence from India's NIFTY Smallcap 250 (arXiv)](https://arxiv.org/pdf/2603.19380) — quantifies survivorship bias in Indian small-cap backtests at ~23% performance inflation.
- [25 Years of Indian IPOs: The Odds of Outperformance (The Calm Investor)](https://thecalminvestor.com/ipos-india/) — published Indian IPO listing-day medians and regime patterns; useful sanity-check benchmark.
- [Post Listing IPO Returns and Performance in India: An Empirical Investigation (IBIMA)](https://ibimapublishing.com/articles/JFSR/2021/418441/) — academic baseline for Indian IPO post-listing performance.
- [SEBI Guidelines for Research Analysts, January 2025](https://www.sebi.gov.in/legal/circulars/jan-2025/guidelines-for-research-analysts_90634.html) — official SEBI RA guidance including AI-usage disclosure and disclaimer requirements.
- [SEBI's Updated Guidelines for Research Analysts & Investment Advisers (Moneylife)](https://www.moneylife.in/article/sebis-updated-guidelines-for-research-analysts-and-investment-advisers-impose-more-compliance-burden/76060.html) — practitioner summary of SEBI 2025 compliance requirements.
- [Navigating the updated regulatory framework for Investment Advisers and Research Analysts (Lexology)](https://www.lexology.com/library/detail.aspx?g=666c5c80-23cb-4217-a261-ac19257cd5b2) — legal analysis of SEBI's RA/RIA boundary.
- [Evaluating Faithfulness in Agentic RAG Systems (MDPI)](https://www.mdpi.com/2504-2289/9/12/309) — faithfulness evaluation in agentic RAG with LLM-judges.
- [Benchmarking LLM Faithfulness in RAG with Evolving Leaderboards (arXiv)](https://arxiv.org/abs/2505.04847) — current state of faithfulness evaluation including known limits of detectors.
- [Mitigating Hallucination in Large Language Models: RAG, Reasoning, and Agentic Systems (arXiv)](https://arxiv.org/html/2510.24476v1) — survey of hallucination mitigation in agentic and RAG systems.
- [RAGAS Metrics Documentation](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) — definitions and limits of RAGAS faithfulness / context-recall / precision.
- [Optimizing LangGraph Cycles: Stopping the Infinite Loop](https://rajatpandit.com/optimizing-langgraph-cycles/) — TTL counters, semantic dedup, and supervisor nodes to prevent agent loops.
- [LangGraph Issue: Agent infinite looping until recursion limit](https://github.com/langchain-ai/langgraph/issues/6731) — observed agent-loop failure modes in production LangGraph.
- [LangChain Issue: Prevent Infinite Tool Call Loop in Customer Support Agent](https://github.com/langchain-ai/langchain/issues/26019) — practical loop-prevention patterns.
- [Why Financial Models Need Calibration Now More Than Ever (Manokhin)](https://valeman.medium.com/why-financial-models-need-calibration-now-more-than-ever-b835a62ddf7a) — calibration metrics, proper scoring rules, monitoring recalibration.
- [MAPIE / Conformal Prediction for Financial Markets](https://www.tildee.com/harnessing-conformal-forecasting-in-financial-markets-quantifying-uncertainty-and-managing-risk-with-mapie/) — distribution-free conformal intervals for financial forecasting.
- [Grey Market Premium (GMP) Explained — How Reliable Is It for IPO Investing? (Lemonn)](https://lemonn.co.in/blog/ipo/grey-market-premium-gmp-ipo-guide/) — GMP is self-reported, unaudited, and weakly predictive — relevant to lookahead-bias prevention.
- [yfinance Issue: No price data for valid NSE/BSE symbol](https://github.com/ranaroussi/yfinance/issues/2612) — documented data-quality issues with Indian tickers on yfinance.
- [yfinance Issue: NSE data unavailable](https://github.com/ranaroussi/yfinance/discussions/2089) — confirmed coverage gaps for Indian markets.
- [Web Scraping and Intellectual Property Rights (IIPRD)](https://www.iiprd.com/web-scraping-and-intellectual-property-rights/) — copyright / redistribution considerations for scraped financial data in India.
- [Beyond Blind Spots: Analytic Hints for Mitigating LLM-Based Evaluation Pitfalls (arXiv)](https://arxiv.org/pdf/2512.16272) — LLM-as-judge limitations: 45–63% error detection alone, up to 74% with domain hints — supports hybrid human+LLM evaluation.
- [Don't Build an ML Portfolio Without These Projects (Towards Data Science)](https://towardsdatascience.com/dont-build-an-ml-portfolio-without-these-projects/) — DS portfolio framing: business impact, technical depth, deployment hygiene.

---
*Pitfalls research for: DRHPLens (agentic-RAG over DRHPs + listing-day forecasting + DS portfolio piece)*
*Researched: 2026-05-28*
