<!-- GSD:project-start source:PROJECT.md -->
## Project

**DRHPLens**

DRHPLens is a web app that lets Indian retail investors ask plain-English questions about an IPO and get an honest, cited, data-grounded assessment of its DRHP/RHP — the 400-page prospectus almost nobody reads. An agentic AI system reads the prospectus, extracts the real signals (risks, financials, promoter background, related-party transactions, use of proceeds), places the company in context against listed peers, and forecasts a calibrated range for listing-day behavior based on historical Indian IPOs.

It is explicitly **informational and educational**, not investment advice.

**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

### Constraints

- **Tech stack**: Web app frontend — Specific framework choice deferred to research phase.
- **Data**: Free/public sources only — SEBI DRHP/RHP PDFs, NSE/BSE historical IPO and price data, screener.in / IR pages for peer fundamentals, `yfinance` (`.NS`/`.BO`) for prices. No paid feeds in v1.
- **Compliance**: Informational/educational only — Required to stay outside SEBI RIA scope and to align with the honesty-first product framing.
- **Scope**: Indian mainboard IPOs (NSE/BSE) — SME segment excluded; non-Indian markets excluded.
- **DS depth**: Project must showcase real modeling — Honest forecasting with proper backtesting, evaluated NLP extraction, and rigorous RAG evaluation — not LLM-only glue code.
- **Budget**: Free / minimal-tier infrastructure — Portfolio project; cloud costs must be near-zero.
- **Audience signal**: Outputs must read as a Data Scientist's work — Evals, calibration, uncertainty, and methodology must be visible artifacts, not buried.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Executive Stack Summary
## Recommended Stack
### Core Technologies
| Technology | Version (May 2026) | Purpose | Why Recommended | Confidence |
|---|---|---|---|---|
| **Python** | 3.11+ | Language | Stable; broad ML/RAG ecosystem; matches every library below. 3.12 also OK; avoid 3.13 until LlamaIndex/Docling fully validate. | HIGH |
| **LangGraph** | 1.2.2 (May 2026) | Agent orchestration | Graph-with-cycles model is the right primitive for the agent loop (retrieve → reason → call peer tool → call forecaster → cite → refine). 1.0 stable shipped Oct 2025, so post-1.x churn is far smaller than the 0.2-era warnings. Best-in-class for state, HITL, streaming, and persistence. | HIGH |
| **LlamaIndex** | 0.14.22 (May 2026) | RAG ingestion + indexing | Best Pythonic abstractions for document-heavy RAG (the DRHP shape is exactly its sweet spot): ingestion pipelines, hierarchical/sentence-window indices, query engines, response synthesizers, native tracing hooks. Pairs cleanly with LangGraph (LlamaIndex as tools called from graph nodes). | HIGH |
| **Docling** | 2.95.0 (May 2026) | Primary DRHP PDF parser | IBM open-source, MIT, **TableFormer** transformer for tables (93.6% benchmark accuracy), layout-aware (titles, sections, lists, figures), native Markdown/JSON export, runs locally (no API fee, no leakage of pre-IPO docs to a third party). The right choice for 300–500-page filings with dense tables. | HIGH |
| **pdfplumber** | 0.11.x | Fallback / table extraction | When Docling misses merged-cell tables (a known weakness on Indian DRHP financial statements), pdfplumber's low-level char/line/rect API is the safety net. Run it on flagged pages only; do not use as primary. | HIGH |
| **PyMuPDF** | 1.27.2 (Apr 2026) | Fast raw text + page splitting | AGPL — fine for portfolio use; switch to PyMuPDF4LLM (markdown) if you want a faster path than Docling on text-only sections. Use for page-level slicing and quick scans. | HIGH |
| **BAAI/bge-m3** | latest HF | Embeddings (primary) | Multilingual (handles Indian-English DRHP idioms and the occasional Hindi/regional company name well), supports dense + sparse + multi-vector in one model, Apache-2.0, runs on CPU at acceptable latency for offline indexing. Solid MTEB performance; widely deployed in 2025–2026 financial RAG stacks. | HIGH |
| **BAAI/bge-reranker-v2-m3** | latest HF | Cross-encoder reranker | Apache-2.0, multilingual, the de-facto open reranker of 2025–2026. Reranks top-50 dense hits to top-5 for the LLM. Critical for DRHP retrieval quality (long, repetitive boilerplate sections — recall is easy, precision is hard). | HIGH |
| **Qdrant** | 1.18.0 (May 2026) | Vector database | Best free self-host story for this scope: docker run, payload filters (essential for filtering by `ipo_id` / `section_type` / `page_range`), native hybrid (dense + sparse) since v1.10, gRPC, and Qdrant Cloud free tier (1GB cluster) as deployment path. Choose over Chroma for query expressiveness and over pgvector when no Postgres is already in play. | HIGH |
| **rank_bm25** | 0.2.2 | Sparse retrieval | Pure-Python BM25 for the hybrid leg. Alternatively, use Qdrant's native sparse vectors (BM25-like) and skip a separate index. | HIGH |
| **Instructor** | 1.15.1 (Apr 2026) | Structured LLM outputs | The standard 2025–2026 library for Pydantic-validated, retried, schema-constrained LLM extraction. Use for the structured-signal extractor (risk factors, RPTs, use of proceeds, promoter background). Works across Gemini/Groq/Anthropic/OpenAI with a uniform API. | HIGH |
| **Pydantic** | 2.x | Schemas + data validation | DRHP-section schemas, forecast feature schemas, API response shapes. Foundation of Instructor; also clean contract surface between the agent and the frontend. | HIGH |
| **Gemini 2.5 Flash** | API | Default reasoning LLM | 1500 req/day free, 1M-token context (can fit full DRHP if needed for ground-truth eval), multimodal (handles DRHP page images for figure/chart extraction in v2). Free tier is sufficient for a portfolio product. | HIGH |
| **Groq (Llama-3.3-70B)** | API | Speed-critical LLM | OpenAI-compatible endpoint, 300+ tok/s, generous free tier. Use as the "fast path" for the routing/planner node; reserve Gemini for the heavier synthesis + citation step. Router pattern across providers multiplies free capacity. | HIGH |
| **scikit-learn** | 1.5+ | ML utilities & baselines | Linear baselines, calibration, pipelines, train/test plumbing, KFold across IPO cohorts. Always present in a DS portfolio. | HIGH |
| **XGBoost** | 2.x | Listing-return regressor | Identified in the 2025 India IPO ML literature as the most effective model for first-day-return forecasting (subscription metrics + issue characteristics + market momentum). Supports quantile regression in 2.0+ (`reg:quantileerror`) for prediction-interval lower/upper estimators. | HIGH |
| **MAPIE** | 1.x (scikit-learn-contrib) | Conformal prediction intervals | The honest-uncertainty layer the project promises. Distribution-free, model-agnostic, wraps the XGBoost regressor to produce calibrated intervals with marginal-coverage guarantees. This is the single library that converts the forecast from "point guess" into a defensible DS artifact. | HIGH |
| **RAGAS** | 0.4.3 (Jan 2026) | RAG metrics | Faithfulness, answer relevancy, context precision, context recall — the four canonical metrics the requirements call for. Reference-free (works on the small synthetic eval set you'll build), LLM-as-judge, integrates with LangChain/LlamaIndex traces. | HIGH |
| **DeepEval** | latest | RAG metrics in CI | Broader metric library and pytest-style runner. Use alongside RAGAS — RAGAS for headline numbers in the report card, DeepEval for the unit-test-style guardrails that fail CI when a metric regresses. | HIGH |
| **Langfuse** | latest (self-host or free cloud) | LLM tracing / observability | Open-source, free cloud tier, captures every agent step (retrieval, rerank, LLM calls, tool calls, citations). Critical artifact for the "DS rigor" narrative — you can show recruiters real traces with metrics attached. Pairs natively with RAGAS scores written back as custom scores. | HIGH |
| **MLflow** | 2.x | Forecast experiment tracking | Free, local-first, no external dependency. Tracks the listing-return model: features, hyperparameters, backtest splits, calibration metrics. Use the local file backend; no need for a server. | HIGH |
| **Streamlit** | 1.x | v1 web frontend | Single-DS shipping reality: Streamlit lets you deliver a recruiter-grade UI in days, with chart rendering (built-in `st.plotly_chart`), citation displays, and easy Hugging Face Spaces deployment. Treat as v1; plan a Next.js upgrade for v2 only if the portfolio audience requires it. | HIGH |
| **Plotly** | 5.x / 6.x | Charts | Peer-multiple bar charts, listing-return histogram + predicted-interval overlay, calibration plots, RAG-metric dashboards. Interactive in Streamlit out of the box. | HIGH |
| **httpx** | 0.27+ | HTTP client | Async-capable; the DRHP ingestion crawler will run faster async. Plays well with retries (`tenacity`) and respectful rate limiting. | HIGH |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---|---|---|---|
| **PyMuPDF4LLM** | latest | Fast markdown extraction | When Docling is overkill (text-only sections, MD&A narrative) and you want sub-second page-to-markdown. |
| **unstructured** | latest | Alternative parser | Only if Docling + pdfplumber both fail on a specific filing layout. Heavyweight install — keep optional. |
| **tiktoken / transformers tokenizers** | latest | Token accounting | Chunk-size budgeting, context-window enforcement, cost estimation. |
| **sentence-transformers** | 3.x | Local embedding inference | Hosts bge-m3 locally; avoids per-call embedding API cost during indexing. |
| **FlagEmbedding** | latest | Reranker inference | Official BAAI library for bge-reranker-v2-m3; faster path than HF Transformers. |
| **rank_bm25** | 0.2.2 | BM25 sparse retrieval | If using a non-Qdrant vector store; otherwise rely on Qdrant native sparse. |
| **yfinance** | 0.2.50+ | Price data (.NS / .BO) | Listing-day close, post-listing trajectory, peer-price history. Yahoo's Indian symbols are reliable for liquid names but can lag for very fresh listings — fall back to NSE bhavcopy via jugaad-data when missing. |
| **jugaad-data** | latest (PyPI) | NSE primary library | Built against the new NSE site (post-deprecation of nsepy). Use for bhavcopy, F&O, RBI rates, listing-day candles where yfinance is patchy. Active community (~524 stars, ~194 forks) but only sporadic releases — pin a known-good commit and budget for occasional patching. **Validate at start of each milestone that NSE site changes haven't broken endpoints.** |
| **nsepython / nsepy-clone** | latest | NSE secondary | Keep as a third fallback only. **Do NOT use nsepy (deprecated, based on old NSE site).** |
| **requests-cache** | latest | Polite scraping | Caches BSE/NSE/screener.in fetches; reduces re-runs and accidental hammering. |
| **beautifulsoup4 + lxml** | latest | HTML scraping | screener.in, chittorgarh DRHP archive page parsing, IR-page tables. |
| **pandas** | 2.2+ | Tabular work | Everywhere. |
| **numpy** | 2.x | Numerical | Everywhere. |
| **polars** | 1.x (optional) | Fast frames | If pandas becomes the bottleneck on multi-year IPO panel construction (unlikely at this scale). |
| **statsmodels** | latest | Calibration / regression | OLS baselines, calibration tests (Spiegelhalter), coefficient interpretability for the DS narrative. |
| **scipy** | latest | Stats | Hypothesis tests on subscription/listing-return relationships, used in EDA. |
| **fastapi** | 0.115+ | API layer (optional v1, required v2) | If you split Streamlit UI from agent core. Good for the eventual Next.js front. |
| **uvicorn** | latest | ASGI server | FastAPI deploys. |
| **tenacity** | latest | Retries | All HTTP calls to SEBI/BSE/NSE/screener.in and all LLM calls. |
| **python-dotenv** | latest | Secrets | Local `.env` for keys; never commit. |
| **rich** | latest | Pretty logs | DS-friendly CLI output during ingestion / eval runs. |
| **typer** | latest | CLI | Wraps ingestion, indexing, eval, and forecast-backtest jobs as discoverable commands. |
| **pytest** | latest | Tests | Required: extractor schema tests, retrieval regression tests, forecaster unit tests. |
| **ruff** | latest | Lint + format | One tool replaces black/flake8/isort. |
| **mypy** | latest (optional) | Types | Pydantic mostly covers this; mypy on the agent/forecasting modules is worth it. |
| **pre-commit** | latest | Git hooks | Ruff + pytest-fast on every commit. |
### Development Tools
| Tool | Purpose | Notes |
|---|---|---|
| **uv** | Package + venv manager | 10-100x faster than pip; the 2025–2026 default. `uv pip install`, `uv run`, lockfile via `uv.lock`. |
| **Docker** | Reproducible local Qdrant + Langfuse | `docker compose up` brings up vector DB + tracing locally. Same compose file deploys to Fly.io. |
| **Jupyter / marimo** | EDA notebooks | marimo is reactive and git-friendly (no JSON-cell-output noise); preferred for portfolio polish. Fall back to plain Jupyter for ML training scratchpads. |
| **DVC** (optional) | Data versioning | Useful if the historical-IPO panel grows large enough that re-downloading is painful. Optional for v1. |
| **GitHub Actions** | CI | Runs ruff + pytest + DeepEval RAG guardrails on PRs. Free for public repos — fits the portfolio. |
| **Hugging Face Spaces** | App hosting | Free CPU 2vCPU/16GB; supports Streamlit, Gradio, FastAPI natively. The right v1 target. |
| **Fly.io free tier** (or Railway) | Qdrant + Langfuse hosting | Or use Qdrant Cloud free (1GB) and Langfuse Cloud free — both are zero-ops paths. |
## Installation
# Python env (Python 3.11+)
# Core RAG + Agent
# PDF parsing
# Embeddings + reranker (local inference)
# Indian data
# ML / forecasting
# Evals + tracing
# Frontend + serving
# Dev
## Stack Patterns by Variant
- Use Gemini `text-embedding-004` or `gemini-embedding-exp` (free tier) instead of local bge-m3.
- Trade: leaks DRHP text to Google; acceptable for *historical* filings (already public), risky to default-on for *fresh* RHPs near pricing.
- Rule of thumb: local bge-m3 for default, remote only when you explicitly need throughput.
- Run pdfplumber on the offending pages; merge results back into the unified document representation.
- Mark those pages in the index with `extraction_quality: "fallback"` so the RAG evals can flag them.
- Skip RAG for that one path; route to Gemini 2.5 Pro/Flash (1M context). RAG is for needle-in-haystack queries; long-context is for whole-section synthesis. The agent should choose the right tool.
- Fall back to `jugaad-data.stock_df()` for NSE bhavcopy; cross-check with BSE history endpoint.
- For *intra-day listing-day* prices, neither library is reliable on day-of — accept this and forecast only on EOD listing close (matches the listing-return target anyway).
- Promote agent core into a FastAPI service; build Next.js 15 + shadcn/ui + Tailwind on top.
- Keep the Streamlit app alive as the "DS console" / internal eval surface.
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|---|---|---|
| **Docling** | LlamaParse (cloud) | If you have a paid LlamaIndex plan and want lowest-friction table parsing. Trade: closed-source, sends DRHP text to a third party, has free quota but it's small. Docling local wins on cost + sovereignty. |
| **Docling** | Reducto / Mistral OCR / Gemini-2.5-Pro PDF | Reducto is the SOTA for messy financial tables, but it is paid. Gemini-2.5-Pro can parse PDFs directly via vision — useful as a "third opinion" extractor in evals. Avoid as primary due to per-PDF cost and reproducibility. |
| **Qdrant** | pgvector | If you already have Postgres in the stack. pgvector is simpler ops; Qdrant has richer filtering and hybrid native. For a greenfield Python-only portfolio, Qdrant wins. |
| **Qdrant** | Chroma | If you want the absolute fastest "uv pip install and go" experience. Chroma is great for prototyping; switch out before v1 ship because filtering and hybrid are weaker. |
| **Qdrant** | LanceDB | If you want embedded (in-process) with no server. Strong choice if you commit to a single-process Streamlit app. Trade: smaller ecosystem of LlamaIndex/LangChain integrations than Qdrant in 2026. |
| **bge-m3 + bge-reranker-v2-m3** | Cohere Embed v4 + Rerank 3.5 | If portfolio audience cares about top-of-MTEB numbers and you accept ~$0 free quota → eventual paid. Open-source is the right narrative for a DS portfolio. |
| **LangGraph** | LlamaIndex Workflows | Workflows is simpler, more Pythonic. Pick it if you find LangGraph's API painful. Trade: less mature cycle/HITL story. The recommended hybrid (LlamaIndex for retrieval, LangGraph for orchestration) is the consensus 2026 pattern. |
| **LangGraph** | Plain Python + asyncio | Tempting for a small project, but a portfolio piece benefits from "I used LangGraph" as a recruiter signal and from the built-in checkpointing for stateful conversations. |
| **Streamlit** | Gradio | Gradio is great for model demos but weak at multi-panel DS dashboards. Streamlit wins for citation displays + charts + tables side-by-side. |
| **Streamlit** | Next.js 15 + FastAPI | The production answer; defer until v2. Don't burn two weeks on shadcn theming before evals are landed. |
| **XGBoost + MAPIE** | LightGBM + MAPIE | Equivalent; pick LightGBM if XGBoost install on your platform misbehaves. Both work with MAPIE. |
| **XGBoost (quantile) + MAPIE conformal** | NGBoost / probabilistic forests | NGBoost gives full predictive distributions, but conformal is the more rigorous + simpler narrative ("distribution-free interval with marginal-coverage guarantee"). Use NGBoost only if a recruiter explicitly cares about it. |
| **RAGAS + DeepEval** | TruLens | TruLens has the best observability UX but smaller community traction in 2026. RAGAS + DeepEval is the more recognizable pair on a resume. |
| **MLflow (local)** | W&B free tier | W&B is prettier (Sweeps, Reports). MLflow stays free + offline-capable. Use W&B if you want a shareable public dashboard for the listing-return model. |
| **Gemini 2.5 Flash** | Groq Llama-3.3-70B as default | Swap order if Gemini quotas tighten further. Pattern is identical; both have OpenAI-compatible endpoints (Groq directly; Gemini via OpenAI-compat layer). |
## What NOT to Use
| Avoid | Why | Use Instead |
|---|---|---|
| **nsepy** | Built against the old NSE website which is being deprecated; library itself is unmaintained. Will break silently. | `jugaad-data` (built on the new NSE site) with `yfinance` as fallback. |
| **PyPDF2 / pypdf (alone) for tables** | No table-structure model; financial statements come out as ragged text. You will silently lose data. | Docling for layout/tables; pdfplumber for low-level fallback. |
| **LangChain 0.x agent constructs (`AgentExecutor`, ReAct-only)** | Pre-LangGraph patterns are now legacy; brittle around state, retries, parallel tool calls. | **LangGraph** for orchestration; use LangChain only as a thin wrapper around LLM clients if at all. |
| **Pinecone for v1** | Free tier exists but is closed-source and adds a vendor dependency for a portfolio project that should read as self-sufficient. | Qdrant (self-host or free cloud tier). |
| **OpenAI as default LLM** | Pay-as-you-go from token #1. Acceptable for evals as a "judge" LLM; bad as the everyday inference engine for a free-tier project. | Gemini 2.5 Flash + Groq, router pattern. |
| **paid Bloomberg / Refinitiv / Capitaline feeds** | Violates the free/public-data constraint and undermines the "I built this end-to-end on public data" portfolio narrative. | SEBI + BSE + NSE archives + screener.in + yfinance + jugaad-data. |
| **Hand-rolled prompt templates without schema validation** | LLM JSON output drifts; downstream code crashes silently on missing fields. | **Instructor + Pydantic** for every structured extraction; treat the schema as the contract. |
| **No evaluation harness ("vibes-based" RAG)** | Project's core promise is anti-hallucination + citation accuracy. A portfolio piece without an eval harness is indistinguishable from every other "I built a RAG app" project. | RAGAS + DeepEval + Langfuse, with a small (50–100 Q/A) hand-curated eval set per DRHP-section type. |
| **Forecasting without backtest splits respecting time** | Naive KFold leaks future IPOs into training; metrics become meaningless. Common DS resume failure mode. | Time-based / cohort-based CV. Walk-forward by listing date. MAPIE on top for intervals. |
| **scraping at full speed without `requests-cache` + delays** | Will get IP-banned from BSE/NSE/screener.in. Loses the data pipeline. | Cache aggressively (DRHPs never change once filed); add jittered delays; respect robots.txt where applicable. |
| **Sending pre-listing RHP text to remote LLMs without thinking** | Public-by-time-of-filing, so technically fine, but it's a habit worth establishing now for v2 (Red-Flag Radar will handle user portfolios = sensitive). | Default to local embeddings (bge-m3) and a single remote LLM call per query. Document this in the architecture as a privacy posture. |
| **Streamlit `st.session_state` as long-term memory** | Lost on rerun; not durable. | Use LangGraph's checkpointer (SQLite locally, Postgres on deploy) for conversation memory; Streamlit only renders. |
## India-Specific Data-Source Notes (read carefully)
| Source | What you get | Caveats |
|---|---|---|
| **SEBI website** (sebi.gov.in) | Authoritative DRHP/RHP filings | No clean API. Page structure changes occasionally; build the scraper defensively (HTML-tolerant, save raw HTML alongside parsed). Each DRHP PDF link is the canonical artifact. |
| **BSE corporate-download URLs** (`bseindia.com/corporates/download/<id>/...`) | Direct PDF links to DRHPs | Numeric IDs are not predictable; you must crawl the listing pages. Some links 404 after a period — **mirror PDFs locally on first fetch**. |
| **NSE archives** (`nsearchives.nseindia.com/corporate/...`) | DRHP/RHP PDFs | NSE has aggressive bot detection on the main site. Use realistic headers, session cookies, and `requests-cache`. The `nsearchives` subdomain is generally more scrape-friendly than the main `nseindia.com`. |
| **chittorgarh.com** | Curated DRHP/RHP archive list, listing-day pricing, subscription metrics | Single best aggregator for **historical-IPO panel construction**. Scrape politely. Pages like `/report/ipo_prospectus_document_drhp_rhp_pdf/20/` are the index; `/ipo/<company>/<id>/` pages have subscription and listing-day data. **This is the single most valuable URL pattern for the project.** |
| **screener.in** | Peer fundamentals, ratios, financials, shareholding | No official API; scrapeable HTML. Sometimes rate-limits aggressively. Cache everything. Be aware: site shows latest data only — for historical fundamentals at the time of a peer comparison snapshot, you may need to combine with IR-page archives. |
| **yfinance with `.NS` / `.BO`** | Listed-equity prices and basic info | Reliable for liquid names; can be incomplete/late for very fresh listings (day-of). Yahoo data quality for Indian names is "good but not authoritative". |
| **jugaad-data** | NSE bhavcopy, F&O, indices | The recommended replacement for the dead `nsepy`. Active enough for portfolio use; **fragile to NSE site changes — keep an integration test that runs nightly.** |
| **company IR pages** | Concall transcripts, annual reports, investor presentations | Useful for peer due-diligence beyond the DRHP. Highly variable HTML — treat as a v2 enhancement. |
## RAG Stack Specifics for DRHP Documents
- **Layout-aware, hierarchical**: Docling extracts sections (Risk Factors, MD&A, Financial Statements, RPTs, Use of Proceeds, Promoter Background). Chunk *within* sections, never across.
- **Page-anchored** for citation: every chunk carries `{drhp_id, section, page_start, page_end}` metadata. NVIDIA's 2024 research showed page-based chunking had the best accuracy + lowest variance on financial docs.
- **Size**: 512–1024 tokens with 100–200 token overlap. Avoid the deprecated "1 page = 1 chunk" pattern (loses local context at page boundaries).
- **Tables = separate index path**: don't embed tables as flat text. Extract them as structured records (Pydantic schemas), store in a sidecar (pandas/SQLite), and let the agent call a `query_financials(drhp_id, line_item)` tool. Embedding tables-as-text is the #1 reason naive RAGs fail on financial docs.
- Hand-curate a **~75-question gold eval set** across 5–10 DRHPs covering: factual lookup, risk extraction, RPT identification, financial-line-item retrieval, multi-hop (across DRHP + peer fundamentals).
- Track in RAGAS + DeepEval + Langfuse: faithfulness, context recall@k (k=5, 10, 30), citation accuracy (custom metric — "did the cited page actually contain the claim"), answer relevancy.
- Treat regression in citation accuracy as a hard CI failure.
## Version Compatibility Notes
| Package | Compatible With | Notes |
|---|---|---|
| **LangGraph 1.2** | LangChain 0.3+, Python 3.10+ | 1.x is stable; breaking-change risk is far smaller than 0.x era. Pin to `>=1.2,<2`. |
| **LlamaIndex 0.14** | Python 3.9+, Pydantic v2 | Many sub-packages (`llama-index-vector-stores-qdrant`, etc.) — keep them all on the same minor version. |
| **Qdrant client 1.18** | Qdrant server 1.13+ | Server image: `qdrant/qdrant:latest`. Sparse-vector API requires 1.10+. |
| **Pydantic v2** | Instructor 1.x, LangGraph 1.x, FastAPI 0.110+, LlamaIndex 0.14 | Universal. Do not regress to Pydantic v1. |
| **Docling 2.95** | Python 3.10+, torch (CPU OK) | First run downloads model weights (~500MB). Cache to a stable `~/.cache/docling`. |
| **XGBoost 2.x + MAPIE** | scikit-learn ≥1.3 | Use `MapieRegressor` with an XGBoost regressor wrapped as a sklearn estimator. |
| **RAGAS 0.4** | LangChain + LlamaIndex tracers; Python 3.10+ | 0.4 changed some metric APIs from 0.3 — read the migration page if porting older code. |
| **Streamlit 1.36+** | Python 3.10+ | Native `st.cache_data` / `st.cache_resource` are essential for keeping bge-m3 + Qdrant client in memory across reruns. |
## Deployment Plan (free-tier-only)
| Component | Where | Cost |
|---|---|---|
| Streamlit app | Hugging Face Spaces (CPU basic, 2vCPU/16GB) | $0 |
| Qdrant | Qdrant Cloud free 1GB cluster, OR self-host on Fly.io free machine | $0 |
| Langfuse | Langfuse Cloud free tier OR self-host on Fly.io | $0 |
| LLM | Gemini 2.5 Flash free (1500 req/day) + Groq free | $0 |
| Embedding inference | Local on the HF Space (bge-m3 on CPU; precompute and cache to disk) | $0 |
| DRHP PDF storage | Hugging Face Datasets (private repo) OR S3-equivalent free tier (e.g., Cloudflare R2 free 10GB) | $0 |
| MLflow tracking | Local file backend, committed artifacts to `mlruns/` | $0 |
| CI | GitHub Actions free (public repo) | $0 |
## Sources
- [LangGraph 1.2.2 on PyPI](https://pypi.org/project/langgraph/) — current stable, post-1.0
- [LlamaIndex 0.14.22 on PyPI](https://pypi.org/project/llama-index/)
- [Docling 2.95.0 on PyPI](https://pypi.org/project/docling/) — IBM, MIT license, TableFormer
- [PyMuPDF 1.27.2 on PyPI](https://pypi.org/project/pymupdf/)
- [Qdrant client 1.18.0 on PyPI](https://pypi.org/project/qdrant-client/)
- [Instructor 1.15.1 on PyPI](https://pypi.org/project/instructor/)
- [RAGAS 0.4.3 on PyPI](https://pypi.org/project/ragas/)
- [jugaad-data on GitHub](https://github.com/jugaad-py/jugaad-data) — primary NSE library (nsepy successor)
- [MAPIE on GitHub](https://github.com/scikit-learn-contrib/MAPIE) — conformal prediction
- [Snowflake — Long-Context Isn't All You Need: Retrieval & Chunking Impact on Finance RAG](https://www.snowflake.com/en/engineering-blog/impact-retrieval-chunking-finance-rag/)
- [Building a Financial RAG System: 90% Recall via Chunking (Medium, Feb 2026)](https://medium.com/@steveinatorx_49018/building-a-financial-rag-system-pt-5-how-i-fixed-chunking-to-reach-90-recall-7f1158e934a9)
- [PDF Table Extraction Showdown: Docling vs LlamaParse vs Unstructured](https://boringbot.substack.com/p/pdf-table-extraction-showdown-docling)
- [Best PDF Parsers for AI and RAG Workflows in 2026 (Firecrawl)](https://www.firecrawl.dev/blog/best-pdf-parsers)
- [Open-source alternatives to Cohere Rerank (ZeroEntropy)](https://zeroentropy.dev/articles/open-source-alternatives-to-cohere-rerank/)
- [Best Embedding Model for RAG 2026 (Milvus)](https://milvus.io/blog/choose-embedding-model-rag-2026.md)
- [Vector Database Benchmarks 2026 (CallSphere)](https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb)
- [Free LLM APIs in 2026 — 13 Providers Compared](https://klymentiev.com/blog/free-llm-api)
- [Predicting IPO first-day returns: Evidence from machine learning analyses (ScienceDirect, 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0378426625001207)
- [IPO Forecasting Using Machine Learning Methodologies: Systematic Review (Indian Journal of Economics & Research)](https://indianjournalofeconomicsandresearch.com/index.php/aijer/article/download/173502/pdf_173/417504)
- [MAPIE paper — distribution-free uncertainty quantification (arXiv 2207.12274)](https://arxiv.org/pdf/2207.12274)
- [Conformalized Quantile Regression (arXiv 1905.03222)](https://arxiv.org/pdf/1905.03222)
- [Hybrid Search Done Right: BM25 + HNSW + RRF (Medium, Feb 2026)](https://ashutoshkumars1ngh.medium.com/hybrid-search-done-right-fixing-rag-retrieval-failures-using-bm25-hnsw-reciprocal-rank-fusion-a73596652d22)
- [RAGAS, TruLens, DeepEval — LLM Evaluation Frameworks (Atlan 2026)](https://atlan.com/know/llm-evaluation-frameworks-compared/)
- [Langfuse — RAG Observability and Evals](https://langfuse.com/blog/2025-10-28-rag-observability-and-evals)
- [LangGraph vs LlamaIndex Workflows — No-BS Guide (Medium, 2025)](https://medium.com/@pedroazevedo6/langgraph-vs-llamaindex-workflows-for-building-agents-the-final-no-bs-guide-2025-11445ef6fadc)
- [Streamlit vs Gradio in 2025 (Squadbase)](https://www.squadbase.dev/en/blog/streamlit-vs-gradio-in-2025-a-framework-comparison-for-ai-apps)
- [Deploying FastAPI on Hugging Face Spaces and its restrictions](https://medium.com/@na.mazaheri/deploying-a-fastapi-app-on-hugging-face-spaces-and-handling-all-its-restrictions-d494d97a78fa)
- [chittorgarh.com IPO Prospectus archive](https://www.chittorgarh.com/report/ipo_prospectus_document_drhp_rhp_pdf/20/) — historical DRHP/RHP index
- RAG stack (LangGraph/LlamaIndex/Qdrant/bge/RAGAS): **HIGH** — verified versions on PyPI, well-trodden 2026 patterns
- PDF parsing (Docling primary, pdfplumber fallback): **HIGH** — Docling benchmark evidence + pdfplumber stability
- LLM choice (Gemini Flash + Groq): **HIGH** — free-tier quotas confirmed, OpenAI-compatible endpoints work today
- India data libs (`jugaad-data`, `yfinance .NS`): **MEDIUM** — both work, but `jugaad-data` release cadence is informal; build an integration test
- Forecasting (XGBoost + MAPIE): **HIGH** — academic literature on Indian IPOs supports XGBoost; MAPIE is the mature conformal library
- Deployment (HF Spaces + Qdrant Cloud free): **HIGH** — both have documented free tiers; HF /tmp restriction is the only gotcha
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

## Project Next Step (CEO review 2026-05-28)

Roadmap committed. Phase 1 is `Foundation + MVP-A (Cited Q&A on One IPO)`. Before planning Phase 1, run the UI design contract step:

```
/gsd-ui-phase 1    # locks UI design contract (citation chips, disclaimer placement, /methodology stub, empty/loading/error states)
/gsd-plan-phase 1  # then create the executable phase plan
```

If you want to skip the UI gate (not recommended for this portfolio piece given UI-03 lays out uncertainty-as-first-class-visual), run `/gsd-plan-phase 1` directly.

CEO-approved cherry-picks landed in `ROADMAP.md`: METHOD-01 (Phase 3 methodology pane), LAND-01 (Phase 6 recruiter landing page), FAILGAL-01 (Phase 6 live failure gallery). Deferred to `TODOS.md`: E5 user upload, E7 retrospectives, E4 Hindi mode, E3 multi-IPO compare. Plan file: `/Users/adityasharma/.claude/plans/mighty-noodling-pretzel.md`.
