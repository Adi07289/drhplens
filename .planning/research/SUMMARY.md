# Research Summary — DRHPLens

**Project:** DRHPLens — Indian-IPO DRHP Decoder for Retail Investors
**Domain:** Agentic RAG + classical ML over Indian IPO prospectuses; DS portfolio web app
**Researched:** 2026-05-28
**Confidence:** HIGH overall (all four research agents agree; tensions resolved below)

---

## Executive Summary

DRHPLens occupies a real gap in the Indian fintech landscape: no existing tool reads the DRHP for the retail investor. Aggregators (Chittorgarh, Trendlyne) link the PDF and display GMP; generic AI tools (ChatPDF, Claude Projects) can answer from a single uploaded document but lack domain grounding, peer context, and historical calibration; enterprise tools (AlphaSense, Bloomberg AskB) are US-centric and enterprise-priced. The product's defensible niche is the intersection of domain-grounded agentic RAG over Indian DRHPs, calibrated listing-day forecasting on historical Indian IPO data, and an honesty-first UX that is simultaneously the right compliance posture. SEBI's January 2025 finfluencer crackdown makes "cited, calibrated, not-advice" a regulatory moat, not just a design philosophy.

The recommended architecture is deliberately non-uniform: deterministic batch pipelines handle ingestion, parsing, chunking, embedding, scraping, and model training; a LangGraph state-machine agent handles only the on-demand reasoning loop; a non-LLM cite-check node enforces citation integrity at every query. This keeps the "magic" auditable. The storage layer (Qdrant vector store + SQLite/Postgres relational + object store) is the integration bus — no pipeline calls another pipeline or calls the agent. The entire system is free-tier deployable on Hugging Face Spaces (app) + Qdrant Cloud free (vector store) + Langfuse Cloud free (tracing), with Gemini 2.5 Flash + Groq as zero-cost LLM providers.

Five CRITICAL design constraints drive every phase-ordering decision: (1) SEBI investment-advice boundary — no verdict language, ever; (2) hallucinated-number prevention via a numeric-faithfulness gate (>=0.95); (3) survivorship-bias elimination by building the historical IPO universe from SEBI issuer filings rather than exchange listing feeds; (4) lookahead prevention via strict available_at timestamps on all forecasting features (GMP and final subscription data must never enter the production model); (5) citation-drift prevention via span-level citations verified by a deterministic cite-check node. Failing any of these five is a portfolio-killer, not just a bug.

---

## Key Findings

### Recommended Stack

Full detail: .planning/research/STACK.md

The stack is open-source-first, free-tier-deployable, and every component is swappable for a managed paid equivalent in v2. Version-pinned for May 2026.

Core technologies:

- LangGraph 1.2.2 — Agent orchestration. Post-1.0 stable; cycles, state, HITL, streaming; best-in-class for a bounded plan->tool->synthesize->cite-check graph
- LlamaIndex 0.14.22 — RAG ingestion + query engines. Document-heavy RAG sweet spot; hierarchical indices; native Qdrant + LangGraph integration
- Docling 2.95.0 — Primary DRHP PDF parser. IBM MIT, TableFormer transformer (93.6% table accuracy), layout-aware, local — no DRHP text leaked to cloud
- pdfplumber 0.11.x — PDF fallback. Handles merged-cell tables Docling misses; run on flagged pages only
- BAAI/bge-m3 latest HF — Embeddings. Multilingual (handles Indian-English DRHP idioms), dense+sparse+multi-vector in one model, Apache-2.0, CPU-viable
- BAAI/bge-reranker-v2-m3 latest HF — Cross-encoder reranker. Apache-2.0, multilingual, de-facto open reranker 2025-2026; top-50 to top-5 precision boost
- Qdrant 1.18.0 — Vector database. Native hybrid (dense+sparse) since v1.10, rich payload filters, free Cloud tier
- Instructor + Pydantic v2 1.15.1 / 2.x — Structured LLM extraction. Schema-validated, retried extraction for risk factors, RPTs, financials, promoter fields
- Gemini 2.5 Flash API — Default LLM. 1500 req/day free, 1M-token context; router pattern with Groq for speed-critical nodes
- Groq Llama-3.3-70B API — Fast-path LLM. 300+ tok/s, generous free tier; use for planner/routing nodes
- XGBoost 2.x — Listing-return regressor. Strongest in 2025 India-IPO ML literature; quantile regression native in 2.0+
- MAPIE 1.x — Conformal prediction intervals. Distribution-free, model-agnostic, marginal-coverage guarantee; wraps XGBoost regressor
- RAGAS + DeepEval 0.4.3 / latest — RAG evaluation. RAGAS for headline faithfulness/recall/precision; DeepEval for pytest-style CI guardrails
- Langfuse latest — LLM tracing / observability. Free cloud tier; captures every agent step; RAGAS scores as custom scores
- MLflow 2.x — Forecast experiment tracking. Free, local-first; tracks training window, CV splits, calibration metrics
- Streamlit 1.36+ — v1 frontend. See frontend decision below
- HF Spaces + Qdrant Cloud free — Zero-cost deployment. 2vCPU/16GB HF Space; 1GB Qdrant Cloud cluster; $0 total

India-specific data sources (keystone):

- chittorgarh.com — single best aggregator for historical IPO panel construction (listing-day price, subscription multiples, DRHP archive index). Most valuable URL pattern for the project.
- yfinance (.NS/.BO) — listed-equity prices; reliable for liquid names; use as convenience layer only; primary is NSE bhavcopy archives (daily CSV).
- jugaad-data — NSE successor to dead nsepy; bhavcopy, F&O, indices; fragile to NSE site changes — keep a nightly integration test.
- screener.in scraping — peer fundamentals (P/E, P/B, ROE, EV/EBITDA); cache aggressively (weekly), throttle, plan a backup source.
- SEBI / BSE / NSE archives — authoritative DRHP/RHP PDFs; no clean API; build defensively with retries and mirror PDFs locally on first fetch.

Do NOT use: nsepy (dead), PyPDF2 alone for tables, LangChain 0.x AgentExecutor, OpenAI as default LLM, Pinecone, paid data feeds.

---

### Expected Features

Full detail: .planning/research/FEATURES.md

Must have — table stakes (P1, v1):

- DRHP ingestion, chunking, indexing — the universal upstream on which everything depends
- Per-IPO snapshot: metadata, plain-English business summary, key financials, risk factor summary, use of proceeds, promoter section — each field citing DRHP page
- Plain-English Q&A with clickable span-level citations (RAG)
- Structured-signal red-flag table (NLP-extracted): RPT %, OFS vs fresh-issue %, customer concentration, promoter pledge %, going-concern mentions, auditor history, debt trajectory — each with an extractor confidence score
- Calibrated listing-day return range (conformal prediction interval, no GMP as feature, backtest visible)
- Peer comparison block (DRHP-disclosed listed peers + screener.in/yfinance fundamentals)
- GMP display, read-only, prominently caveated, computationally isolated from the forecast model
- Anti-hallucination guardrails: refusal on ungrounded asks, faithfulness threshold enforced
- Eval harness with visible metrics: faithfulness, retrieval recall@k, citation accuracy, forecast calibration/MAE/interval coverage
- Not-advice framing throughout: persistent footer, first-use modal, per-answer note, no prescriptive language

Should have — differentiators (P2, v1.x post-launch):

- Agentic multi-step Q&A — trigger: faithfulness > 0.85 on gold set
- Historical cohort comparison ("among IPOs with this profile, N=14, median listing +6%") — trigger: dataset reaches sufficient size
- "Show your work" methodology pane (expandable traces per claim) — trigger: agent traces instrumented end-to-end
- "What this DRHP doesn't say" panel (expected-disclosures checklist)
- Post-listing calibration recap pages (T+5, T+30, T+90 actuals vs predicted)
- Broader IPO coverage (automated ingestion pipeline)

Defer (v2+):
- Portfolio Red-Flag Radar (requires user accounts, broader filings ingestion, new compliance posture)
- SME IPO support (separate disclosure regime, weaker signal quality)
- Mobile-native app
- Multilingual UI (Hindi at minimum)
- Subscription SaaS tier

Anti-features (explicitly not building):
- Subscribe / avoid verdict — SEBI RIA violation and undermines the honesty-first positioning
- GMP-based forecasting — circular (GMP encodes listing expectations); display GMP read-only and let the gap between GMP and the GMP-free model output be the signal
- Personalized portfolio integration — scope creep and SEBI advisor-registration concern
- Social sentiment scraping (Twitter/Telegram) — imports the noise the product exists to filter

---

### Architecture Approach

Full detail: .planning/research/ARCHITECTURE.md

The system has three distinct tiers that must never be conflated: (1) deterministic batch pipelines at the edges (ingestion, parsing, chunking, embedding, historical-IPO scraping, model training), (2) a LangGraph state-machine agent in the middle (classify_intent -> plan -> tool_loop[bounded] -> synthesize -> cite_check), and (3) a storage bus that decouples them (Qdrant vector store, SQLite/Postgres relational DB, object store, run/eval log, parquet feature store). Components communicate through storage, never through direct calls.

Four foundational components:

1. C9/C10/C11 — DRHP Ingestor + PDF Parser + Chunker/Embedder (batch): the universal upstream. Section-aware chunking (never split across section boundaries); every chunk carries {drhp_id, section, page_start, page_end} metadata; tables extracted separately as Pydantic-schematized records stored in the relational DB, not embedded as flat text.
2. C3 — Agent Orchestrator (on-demand): LangGraph state machine with a hard TTL step counter and semantic dedup of tool calls within a trace. The cite-check node is a deterministic code node (not an LLM call) that verifies every claim span has at least one resolved source ID from the retrieved set.
3. C4 — Retriever (on-demand): hybrid BM25 (sparse) + bge-m3 (dense) -> RRF fusion -> top-30 -> bge-reranker-v2-m3 cross-encoder -> top-5. Always filtered by ipo_id and optionally section_type.
4. C13/C7 — Forecast Trainer + Forecaster Tool (batch train, on-demand serve): XGBoost regressor wrapped with MAPIE conformal predictor. Features must be available_at <= T0 (issue-open day). Walk-forward CV only; four baselines reported; beat-baseline is a release gate.

Retrieval pipeline (concrete): BM25 + bge-m3 -> top-50 per leg -> RRF -> top-30 -> bge-reranker -> top-5 -> Gemini 2.5 Flash with cite-every-claim constraint -> cite-check node -> emit.

Eval hooks (always-on):
- H1: Retrieval recall@k (nightly + pre-deploy)
- H2: Faithfulness + citation coverage (per-run online + nightly offline)
- H3: Extraction F1 vs hand-labeled gold (manual + on model change)
- H4: Forecast MAE / conformal coverage / PIT histogram (each training run)
- H5: Agent operational — success rate, p50/p95 latency, token cost/run, failure taxonomy (always-on)
- H6: Feature drift PSI + rolling backtest performance (weekly)

Key structural invariant: Batch pipelines (C9-C13) never call the agent (C3). The agent only reads from storage. Extraction (C6) is on-demand first time, then cached to the relational DB — the primary cost-and-latency lever.

---

### Critical Pitfalls

Full detail: .planning/research/PITFALLS.md — 21 pitfalls with recovery strategies and a "Looks Done But Isn't" exit checklist

5 CRITICAL (portfolio-killers; must be designed against from Phase 0, not retrofitted):

1. SEBI investment-advice boundary — hard-coded banned-token scrubber (buy, sell, subscribe, avoid, recommend, target price, fair value) in agent system prompt and output filter; every page carries a persistent above-the-fold disclaimer; no personalization fields; forecast always emits a range with calibrated hit-rate, never a point verdict. Legal review checkpoint before public launch.

2. Hallucinated numbers — two-stage answer protocol: (a) retrieve and extract structured candidates as {page, table, row, column, value, unit, fiscal_year} objects; (b) LLM generates prose by referencing the structured object only. Every numeric claim carries the source tag. Regex-extract all numerical claims post-generation, re-retrieve their cited spans, run per-claim NLI faithfulness check. Gate: numeric faithfulness >= 0.95 on a 50-query eval set before launch.

3. Survivorship bias in historical IPO dataset — build the universe from SEBI offer-document list (DRHP filings), not exchange listing feeds. Every IPO row has an explicit status column: withdrawn, listed_alive, delisted, merged, name_changed. Replace-with-NaN on missing prices, never drop. Sanity-check: if your median listing return materially exceeds the published ~7% academic baseline, assume survivorship bias until proven otherwise.

4. Lookahead from GMP / final subscription / post-issue features — every feature has an available_at timestamp; reject any feature where available_at > T0 (issue-open). GMP and final subscription multiples belong only in a clearly-labeled post_close variant model, never in the production pre_apply model. Walk-forward / expanding-window CV only; no random k-fold across years. Any model R^2 > 0.5 on listing-day return is a red flag for leakage.

5. Citation drift / wrong-page citations — span-level citations (character offsets), not page-level. LLM emits a claim_id; the renderer resolves the citation from the retrieval object. Cite-check node validates each citation against the retrieved set before emission. Gate: >=95% of citations land on the actual claim text in a 50-query click-through audit. Store both PDF-index page number and printed page number (DRHPs restart pagination after Roman-numeral front matter).

Top HIGH pitfalls (credibility collapse in DS interview):

- All-LLM-glue / no real modeling (P11) — time-budget contract: >=35-40% of build time on non-LLM modeling; at least two non-LLM artifacts; model card for the forecaster. Cut agent scope before cutting modeling scope.
- Naive baselines beat the model silently (P9) — mandatory reporting of four baselines with significance test. If model fails to beat baseline, the portfolio piece says so honestly.
- Evaluation theater (P10) — every headline metric gets an interpretation paragraph, failure gallery, and human spot-check (>=50 examples alongside LLM-judge metrics).
- Risk-factor boilerplate inflates extraction metrics (P12) — IDF-weight extracted risks; split into issuer_specific_risks vs industry_standard_risks; evaluate on issuer-specific recall.
- Regime-shift blindness (P6) — include regime indicator features (NIFTY trailing 6M return, India VIX, IPO-pipeline-density); walk-forward with per-year RMSE; conformal intervals.

---

## Implications for Roadmap

The phase sequence below is the canonical build order derived from all four research files. It is dependency-driven, DS-signal ordered, and anti-pitfall mapped.

### Phase 1: Foundation + Vertical-Slice MVP-A

Rationale: Ship the thinnest possible end-to-end demo before going deep on any layer. End-to-end means: one hardcoded IPO, user asks a question, gets a cited prose answer with clickable span-level citations. This already differentiates from "ChatGPT pasted a DRHP." Compliance posture and storage adapters must be solid here because everything downstream depends on them.

Delivers: MVP-A — cited Q&A on one IPO, demoable via Loom + deployed on HF Spaces.

Components: C9 (manual PDF download), C10 (basic parser), C11 (naive chunker + embedder), C4 (vector-only retriever), C3 (minimal LangGraph: retrieve -> synthesize -> cite_check), C2 (FastAPI /ask endpoint), C1 (Streamlit chat with citation rendering), C17 (run log and storage adapters).

Features: Plain-English Q&A with citations, citation infrastructure, not-advice framing, anti-hallucination (refusal patterns), mobile-responsive UI.

Pitfalls owned: SEBI boundary (P1) — banned-token scrubber and disclaimer infrastructure. Citation drift (P5) — span-level citation system from day one. Demo-day fragility (P19) — pre-index corpus, cache LLM responses, warm-keep the app. Scope creep (P20) — phase gate: do not proceed until MVP-A is deployed and demoable.

Research flag: Standard patterns; no additional research phase needed.

---

### Phase 2: DRHP Extraction Pipeline + Multi-IPO

Rationale: The structured-signal extractor is the first distinctly DS artifact. It requires section-aware parsing, Pydantic-schematized output via Instructor, and a hand-labeled gold set to evaluate against. This phase also automates multi-IPO ingestion, making the product a catalogue rather than a single-document demo.

Delivers: MVP-B — per-IPO snapshot page with structured red-flag table (RPT %, OFS %, pledge %, going-concern mentions, debt trajectory, customer concentration), each field with a confidence score and extraction eval F1. 5-10 IPOs in catalogue.

Components: C9 (automated DRHP discovery from SEBI/BSE), C10 (upgraded section-aware parser), C11 (upgraded structure-aware chunker with parent-document pointers), C6 (Structured Extractor: Instructor + Pydantic v2 + regex rules), eval/gold/extraction_labels.jsonl (hand-label ~20-30 DRHPs), H3 (extraction F1 pipeline). Hybrid retrieval (BM25 + dense + rerank) also upgrades here.

Features: Structured-signal red-flag table, business model summary, risk factor prioritization, use of proceeds breakdown (OFS vs fresh-issue prominence), promoter/management section, per-IPO snapshot page.

Pitfalls owned: Hallucinated numbers (P2) — two-stage structured extraction protocol. Risk-factor boilerplate (P12) — IDF-weighting and issuer-specific vs boilerplate split. Brittle DRHP ingestion (P14) — multi-source redundancy, SHA versioning, DRHP vs RHP discrimination. Embedding mismatch on Indian-English (P13) — evaluate two embeddings; implement hybrid retrieval.

Research flag: Standard patterns for Instructor extraction; no additional research phase needed.

---

### Phase 3: Historical IPO Dataset + Peer Comparator

Rationale: This phase builds the data moat — a clean historical Indian mainboard IPO dataset (2014-present, ~800-1000 IPOs) that is survivorship-corrected and feature-rich. The peer comparator becomes the first agent tool that reaches outside the DRHP. Together they enable MVP-C and lay the feature engineering foundation for the forecaster.

Delivers: MVP-C — cited Q&A + DRHP extraction + live peer comparison table (P/E, P/B, EV/EBITDA, ROE vs DRHP-disclosed listed peers).

Components: C12 (Historical IPO Scraper: BSE/NSE/yfinance/screener.in/chittorgarh), C15 (relational DB schema: IPOs table with status column, peers, prices, structured-extract cache), C5 (Peer Comparator tool), GMP display (read-only, isolated from model), UI: peer table component + GMP panel.

Data sources activated: chittorgarh.com, yfinance .NS/.BO (secondary; NSE bhavcopy archives are primary), screener.in (peer fundamentals — cache weekly, throttle, plan backup), jugaad-data (NSE bhavcopy).

Features: Peer comparison block, GMP display (read-only), basic IPO metadata pane.

Pitfalls owned: Survivorship bias (P3) — SEBI-sourced universe, explicit status column, replace-with-NaN on missing prices, median sanity check against ~7% published baseline. yfinance data quality (P15) — NSE bhavcopy as primary, corporate-actions ledger, listing-day price audit. Screener.in ToS / rate limits (P16) — aggressive caching, throttling, backup source list.

Research flag: Run a jugaad-data endpoint validation spike before committing to it as the primary NSE source.

---

### Phase 4: Listing-Day Forecaster (Core DS Artifact)

Rationale: This is the highest-risk, highest-DS-signal phase. Allocate the most time here. The conformal-prediction forecaster is the headline portfolio output that a DS interviewer will scrutinize most carefully. Walk-forward CV, baselines, calibration plots, MAPIE intervals, and a model card are all exit criteria. Feature engineering must respect strict available_at temporal constraints. This phase must NOT rush to ship before the baseline is built and beaten.

Delivers: MVP-D — The full DRHPLens v1: cited Q&A + extraction + peer comparison + calibrated listing-day return range (80%/95% conformal intervals, no GMP as feature, backtest visible in methodology pane) + four baselines reported.

Components: ml/features.py (deterministic feature builders, all with available_at <= T0), ml/models/baseline.py (four baselines — beat-baseline is a release gate), ml/models/gbm.py (XGBoost regressor), ml/calibration.py (MAPIE conformal wrapper), ml/backtest.py (walk-forward CV), C13 (training pipeline + MLflow artifact registry), C7 (Forecaster tool), H4 (coverage + PIT + MAE dashboard), UI: forecast chart + methodology pane with model card.

Features: Calibrated listing-day return range, honest uncertainty UI (intervals as primary visual, not point estimate), methodology pane.

Pitfalls owned: Lookahead bias (P4) — feature available_at audit; walk-forward only. Regime-shift blindness (P6) — regime indicator features; per-year RMSE. Small-N sector slices (P7) — N-per-sector reported; sectors < 30 pooled. Naive baselines beat the model (P9) — four baselines with significance test. Calibration theater (P17) — empirical coverage on test set; conformal intervals. All-LLM-glue (P11) — this phase is the non-LLM modeling budget; model card + ablations required. UX implies advice (P21) — interval is the main visual; no green/red coding.

Research flag: India-IPO feature engineering from public data has no open reference implementation — plan one EDA week in notebooks before committing to the feature set.

---

### Phase 5: Full Agent + Eval Harness + Portfolio Polish

Rationale: Earlier phases have built the tools and storage. This phase upgrades the agent to full multi-step reasoning (all five tools active), brings the eval harness to dashboard quality, and surfaces the DS rigor story visibly in the UI. This converts a working product into an impressive portfolio artifact. Frontend re-evaluation gate (Streamlit vs Next.js) happens here.

Delivers: Fully polished DRHPLens — agentic multi-step Q&A, full eval dashboard committed to /eval-reports/ in the repo, methodology pane linking to reports, "Show your work" expandable traces, GMP-vs-model comparison as an explicit honest signal, post-listing calibration recap pages.

Components: Upgrade C3 to full LangGraph multi-tool orchestration, eval/gold/qa_pairs.jsonl (50-100 hand-labeled Q->passage pairs across 5-10 DRHPs), H1 (RAGAS retrieval evals), H2 (RAGAS faithfulness + DeepEval citation-coverage CI guardrails), H5 (agent operational dashboards), eval/reports/ (committed HTML dashboards per release), "Show your work" UI panel, methodology page (public, paper-like README). Legal review checkpoint before public launch.

Features: Agentic multi-step Q&A, eval harness with visible metrics, "Show your work" methodology pane, historical cohort comparison view (KNN over historical IPO features), post-listing calibration recap, Indian-context formatters (lakh/crore, glossary tooltips).

Pitfalls owned: Agent infinite loops (P8) — TTL step counter + semantic call dedup + supervisor node stress-tested. Agent answers without retrieving (P18) — retrieval-mandatory contract + output-schema enforcement. Evaluation theater (P10) — every headline metric gets interpretation paragraph + failure gallery + human spot-check. SEBI boundary (P1) — legal review checkpoint.

Research flag: DeepEval CI integration and Langfuse custom-score callbacks may need a brief exploration spike at phase start.

---

### Phase Ordering Rationale

- Ingestion (Phases 1-2) must precede retrieval, which must precede the agent, which must precede eval.
- The historical IPO dataset (Phase 3) must be built before the forecaster (Phase 4) because the forecaster's features come from that dataset.
- The structured extractor (Phase 2) feeds the forecaster's feature vector — NLP artifacts must exist before feature engineering.
- Eval harness polish (Phase 5) depends on all prior artifacts existing; but eval hooks must be instrumented from Phase 1 onward.
- The agent upgrade to multi-tool (Phase 5) is gated on Phase 3-4 tools being stable, tested, and cached.

---

### Frontend Decision: Streamlit (Phases 1-4) with Explicit Re-Evaluation Gate at Phase 4 Exit

STACK.md recommends Streamlit for v1 shipping speed. ARCHITECTURE.md notes Next.js gives a stronger portfolio artifact and is the correct v2 production choice.

Resolution: Use Streamlit for Phases 1-4. Evaluate migration at Phase 4 exit. The FastAPI API layer should be present from Phase 1 even under Streamlit — this makes the migration cheap if chosen.

Migration trigger (evaluate all three at Phase 4 exit):
- Is the forecasting + RAG story compelling enough that portfolio presentation matters more than shipping speed?
- Do you have 2-3 weeks to spare before portfolio-ready date?
- Are there recruiters in the target audience who specifically expect a polished Next.js web UI?

If yes to all three: migrate to Next.js + FastAPI split. Otherwise: Streamlit is the right call.

---

### Research Flags

Phases with standard patterns (no research-phase needed):
- Phase 1: LangGraph + LlamaIndex + Streamlit + Docling patterns are well-documented in 2026.
- Phase 2: Instructor + Pydantic extraction patterns are well-documented.
- Phase 5: RAGAS + DeepEval + Langfuse integration is standard.

Phases warranting an exploration spike at phase start:
- Phase 3: jugaad-data endpoint stability changes with NSE site updates — run a validation spike before committing to it as the primary NSE source. (~1 day)
- Phase 4: India-IPO feature engineering from public data has no open reference implementation — plan one EDA week in notebooks before committing to the feature set. (~5 days)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified on PyPI (May 2026). Library choices are standard 2025-2026 financial RAG patterns. One exception: jugaad-data (MEDIUM — informal release cadence; pin a known-good commit and add a nightly integration test). |
| Features | HIGH | Competitor landscape well-researched; table-stakes and differentiator categories internally consistent; anti-features clearly grounded in SEBI regulations. MEDIUM on some differentiator design specifics. |
| Architecture | HIGH | Overall shape is well-trodden (agentic RAG + classical ML + eval harness). LangGraph state-machine is the consensus 2026 approach. |
| Pitfalls | HIGH for SEBI / survivorship / RAG-eval pitfalls (official docs + academic sources). MEDIUM for India-specific data-source instability and DS-portfolio-framing pitfalls. | |

Overall confidence: HIGH

### Gaps to Address During Planning

1. jugaad-data endpoint stability — NSE site has changed before and will change again. Run a validation spike at Phase 3 start; set up a nightly integration test as a CI job.

2. Docling table extraction on Indian DRHPs — TableFormer is benchmarked on general financial docs, not specifically Indian DRHP formats (inconsistently merged cells, non-standard financial statement layouts). Budget for a pdfplumber fallback path; mark pages with extraction_quality: "fallback" in the index.

3. India-IPO feature engineering from public data — academic papers use proprietary or cleaned datasets. The project must reconstruct what-was-knowable-on-T0 from public sources for each historical IPO. Plan one EDA week in Phase 4 notebooks before committing to the feature set.

4. screener.in data stability — no official API; HTML structure changes without notice. Establish a backup peer-fundamentals source before relying on screener.in in production.

5. HF Spaces cold-start — the free-tier Space hibernates after inactivity. Pre-index a fixed corpus of 20-50 IPOs; implement a cron pinger; document the offline demo video path before any high-stakes demo.

6. SEBI legal review — brief informal review with someone who knows SEBI RA/RIA regulations before public launch. Phase 5 gate item.

---

## Cross-Cutting Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Frontend: Streamlit vs Next.js | Streamlit for Phases 1-4; re-evaluation gate at Phase 4 exit | Ship speed and DS-story first; UI polish is Phase 5 optionality, not Phase 1 bloat |
| GMP: display vs model input | Display read-only, computationally isolated from the forecast model | GMP in the model is circular and compliance-questionable; the gap between GMP and the GMP-free model output is the honest signal |
| Agent: bounded state machine vs freeform ReAct | Bounded LangGraph state machine (plan -> tool_loop[TTL] -> synthesize -> cite_check) | Predictability, observability, testability; cite-check node can only exist as a deterministic graph node |
| Storage as integration bus | Batch pipelines write; on-demand tools read; no direct pipeline-to-pipeline calls | Single-developer maintainability and future v2 reuse; the same storage bus will power the Portfolio Red-Flag Radar |
| Compliance posture | Hardcoded at system-prompt and output-renderer level, not only in product copy | The SEBI boundary is behavioral (does it function as advice?), not linguistic |
| Non-LLM modeling budget | >=35-40% of total build time | Portfolio target is DS, not ML Engineer; a project without substantive non-LLM modeling is indistinguishable from an API-composition demo |
| Eval harness | Instrumented from Phase 1; dashboard-quality by Phase 5 | Without evals there is no feedback loop and no visible DS-rigor artifact; building them last is the most common failure mode |

---

## Sources

All sources are documented in full in the four dimension files. Aggregate by tier:

Primary (HIGH confidence — verified versions, official docs, academic papers):
- LangGraph 1.2.2, LlamaIndex 0.14.22, Docling 2.95.0, Qdrant 1.18.0, Instructor 1.15.1, RAGAS 0.4.3 — all on PyPI (May 2026)
- SEBI Guidelines for Research Analysts, January 2025 (sebi.gov.in) — official RA/RIA boundary and AI-disclosure requirement
- MAPIE (arXiv 2207.12274) and Conformalized Quantile Regression (arXiv 1905.03222) — conformal interval theory
- Predicting IPO first-day returns via ML (ScienceDirect 2025) — XGBoost as best Indian-IPO forecaster
- Survivorship bias in Indian small-caps (arXiv 2603.19380) — ~23% performance inflation without survivorship correction
- Snowflake Engineering: Long-Context Isn't All You Need (finance RAG chunking) — page-anchored chunking recommendation
- SEBI finfluencer crackdown: 15,000+ entities removed (BusinessToday 2024) — regulatory moat context
- chittorgarh.com IPO archive — historical IPO data keystone confirmed

Secondary (MEDIUM confidence — community consensus, multiple sources):
- LangGraph vs ReAct pattern analysis (Amitav Roy 2025, Mager.co 2026)
- Hybrid search BM25+HNSW+RRF (Medium Feb 2026)
- jugaad-data GitHub (524 stars, 194 forks) — NSE successor status
- 25 Years of Indian IPOs (The Calm Investor) — published ~7% median baseline for sanity-check
- Indian IPO GMP correlation literature (IPO Guru, Sahi) — ~80% GMP/listing correlation on mainboard
- yfinance Indian ticker issues (GitHub issues #2612, #2089) — documented data gaps

Tertiary (contextual, not load-bearing):
- Competitor analysis (Chittorgarh, Trendlyne, Tickertape, AlphaSense) — public product pages
- DS portfolio framing pitfalls (Towards Data Science) — industry consensus

---

## Dimension File Pointers

| File | What to read it for |
|------|---------------------|
| .planning/research/STACK.md | Exact version pins, install commands, India-specific data-source notes, deployment plan, full alternatives-considered table, What NOT to Use list |
| .planning/research/FEATURES.md | Full competitor feature matrix, SEBI compliance constraints honored, Indian retail mental model, complete feature dependency graph, v2 feature list |
| .planning/research/ARCHITECTURE.md | Full 19-component diagram with responsibilities, complete data-flow walkthrough, 6 architecture patterns with trade-offs, anti-pattern gallery, vertical-slice MVP build sequence |
| .planning/research/PITFALLS.md | All 21 pitfalls with warning signs, recovery strategies, Looks Done But Isn't exit checklist, technical debt patterns, security/compliance mistakes, UX pitfalls |

---
Research synthesis completed: 2026-05-28
Dimension files synthesized: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
Ready for requirements definition and roadmap: yes
