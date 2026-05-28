# Architecture Research — DRHPLens

**Domain:** Agentic RAG over long Indian IPO prospectuses, fused with a historical-IPO listing-day forecasting model and peer-comparison tools. Portfolio piece optimized for Data Scientist signal.
**Researched:** 2026-05-28
**Confidence:** HIGH on overall shape (well-trodden patterns: agentic RAG + classical ML + eval harness). MEDIUM on specific component choices that overlap with STACK.md.

---

## 1. Architectural Thesis

Three principles drive the structure:

1. **Determinism at the edges, agency in the middle.** Ingestion, indexing, scraping, model training, and backtesting are deterministic batch pipelines. The agent's tool-calling loop is the *only* non-deterministic surface. This keeps the "magic" auditable.
2. **DS hooks are first-class, not afterthoughts.** Evaluation harnesses (RAG faithfulness/recall, forecast calibration, extraction F1) attach at well-defined seams. Every agent run is traceable; every model has a baseline and a held-out backtest.
3. **Storage is the integration layer.** Components don't call each other directly. They read/write to a small set of stores (object store, vector store, relational DB, run log). This is what lets a one-person project ship without micro-service hell — and what lets the v2 Portfolio Red-Flag Radar reuse the engine.

---

## 2. System Overview

### 2.1 Layered diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION  (on-demand, user-facing)                  │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │ Web Frontend: chat UI · citation rendering · methodology pane ·    │      │
│  │ peer table · forecast chart · "Not investment advice" banner       │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                  │  HTTP/WS                                   │
├──────────────────────────────────┼───────────────────────────────────────────┤
│                          API GATEWAY  (FastAPI)                               │
│   /ipos · /ask  (streams)  · /runs/{id}  · /eval/reports  · /health           │
├──────────────────────────────────┼───────────────────────────────────────────┤
│                       AGENT ORCHESTRATION  (on-demand)                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │            LangGraph state machine (Planner → Tools → Critic)        │    │
│  │  Nodes: classify_intent → plan → tool_loop → synthesize → cite_check │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│         │            │             │              │              │           │
│      ┌──▼──┐      ┌──▼──┐      ┌──▼──┐        ┌──▼──┐        ┌──▼──┐        │
│      │ RAG │      │Peer │      │Struct│        │Fore- │       │Chart│        │
│      │tool │      │tool │      │Extract│       │cast  │       │tool │        │
│      └──┬──┘      └──┬──┘      └──┬──┘        └──┬──┘        └──┬──┘        │
├─────────┼────────────┼────────────┼──────────────┼──────────────┼───────────┤
│         │            │            │              │              │           │
│    DOMAIN SERVICES (stateless, callable as Python modules + tool wrappers)   │
│  ┌──────▼──────┐ ┌──▼─────────┐ ┌▼──────────┐ ┌▼──────────────┐ ┌─────────┐│
│  │ Retriever   │ │ Peer       │ │ Extractor │ │ Forecaster    │ │ Charter ││
│  │ (hybrid     │ │ Comparator │ │ (LLM +    │ │ (sklearn/     │ │ (plotly/││
│  │ BM25+vector │ │            │ │ regex/    │ │ statsmodels   │ │ matplot)││
│  │ + rerank)   │ │            │ │ rules)    │ │ + conformal)  │ │         ││
│  └──────┬──────┘ └──┬─────────┘ └─┬─────────┘ └──┬────────────┘ └─────────┘│
├─────────┼───────────┼─────────────┼──────────────┼──────────────────────────┤
│         │           │             │              │                          │
│                    STORAGE  (the integration bus)                            │
│  ┌──────▼─────┐ ┌───▼──────┐ ┌────▼──────┐ ┌────▼────────┐ ┌─────────────┐  │
│  │ Vector DB  │ │ Relational│ │ Object    │ │ Run/Eval    │ │ Feature     │  │
│  │ (Qdrant /  │ │ DB        │ │ store     │ │ log         │ │ store       │  │
│  │ pgvector)  │ │ (Postgres │ │ (S3-       │ │ (LangSmith/ │ │ (parquet on │  │
│  │ chunks +   │ │ /SQLite): │ │ compatible │ │ Phoenix +   │ │ disk; small)│  │
│  │ embeddings │ │ IPOs,     │ │ R2/MinIO/  │ │ Postgres    │ │             │  │
│  │            │ │ peers,    │ │ local):    │ │ traces)     │ │             │  │
│  │            │ │ prices,   │ │ raw PDFs, │ │             │ │             │  │
│  │            │ │ extracts  │ │ parsed    │ │             │ │             │  │
│  │            │ │           │ │ JSON      │ │             │ │             │  │
│  └────────────┘ └───────────┘ └───────────┘ └─────────────┘ └─────────────┘  │
├──────────────────────────────────────────────────────────────────────────────┤
│                       BATCH PIPELINES  (offline, scheduled / manual)          │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │ DRHP/RHP   │ │ PDF Parse  │ │ Chunk +  │ │ Historical│ │ Forecast model  │ │
│  │ Ingestor   │ │ + Section  │ │ Embed    │ │ IPO       │ │ Training +      │ │
│  │ (SEBI/BSE/ │ │ Tagger     │ │ (struct- │ │ Scraper   │ │ Backtest        │ │
│  │  NSE)      │ │            │ │ aware)   │ │ (BSE/NSE/ │ │ (sklearn +      │ │
│  │            │ │            │ │          │ │ yfinance/ │ │ conformal +     │ │
│  │            │ │            │ │          │ │ screener) │ │ time-series CV) │ │
│  └────────────┘ └────────────┘ └──────────┘ └──────────┘ └─────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                       EVAL HARNESS  (cross-cutting, ALWAYS-ON)                │
│  RAG evals (Ragas/Phoenix): faithfulness · recall@k · citation accuracy       │
│  Extraction evals: field-level F1 vs hand-labeled gold set                    │
│  Forecast evals: time-series-CV MAE · calibration (PIT) · interval coverage   │
│  Agent traces: every tool call · token spend · failure modes                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component responsibilities

| # | Component | Owns | Layer | Mode |
|---|-----------|------|-------|------|
| C1 | **Web Frontend** | Chat UI, citation rendering, peer table, forecast chart, "not advice" banner | Presentation | on-demand |
| C2 | **API Gateway** | Auth (light/none for v1), request routing, run-id issuance, SSE streaming of agent steps | Presentation | on-demand |
| C3 | **Agent Orchestrator** | Plans, calls tools, retries, decides when to stop, ensures every claim has a citation | Orchestration | on-demand |
| C4 | **RAG Tool / Retriever** | Hybrid retrieval over DRHP chunks with metadata filtering by `ipo_id`, section, page; cross-encoder rerank | Domain service | on-demand |
| C5 | **Peer Comparator Tool** | Given an IPO, returns N peers + a multiples table (P/E, EV/EBITDA, P/S, ROE, debt/equity, growth) | Domain service | on-demand |
| C6 | **Structured Extractor Tool** | DRHP → JSON: risk factors (categorized), financial snapshot, RPTs, promoter, use of proceeds, GMP-irrelevant red flags | Domain service | on-demand at first call, **cached** to relational DB |
| C7 | **Forecaster Tool** | Given DRHP-derived + market features → listing-day return distribution (median + 80/95% interval) | Domain service | on-demand (model loaded once) |
| C8 | **Charter Tool** | Plotly/matplotlib spec generation for peer comparisons and forecast distributions | Domain service | on-demand |
| C9 | **DRHP Ingestor** | Discover + download new DRHP/RHP PDFs from SEBI/BSE/NSE; dedupe; metadata extraction | Batch pipeline | scheduled (daily) |
| C10 | **PDF Parser** | DRHP PDF → structured sections + tables + page-level text; handles 300–500-page docs robustly | Batch pipeline | per-IPO once |
| C11 | **Chunker + Embedder** | Section-aware chunking with parent-document references; embedding generation; vector upsert | Batch pipeline | per-IPO once |
| C12 | **Historical IPO Scraper** | Past Indian mainboard IPOs: issue prices, listing-day OHLC, subscription data, peer mapping | Batch pipeline | scheduled (weekly) |
| C13 | **Forecast Trainer** | Feature engineering, time-aware CV, model selection, conformal calibration; emits versioned artifact | Batch pipeline | manual / on data drift |
| C14 | **Vector Store** | Chunk embeddings + metadata; hybrid (BM25 + dense) | Storage | persistent |
| C15 | **Relational DB** | IPOs table, peers table, prices table, structured-extract cache, run metadata | Storage | persistent |
| C16 | **Object Store** | Raw PDFs, parsed-JSON intermediates, model artifacts, eval reports | Storage | persistent |
| C17 | **Run/Eval Log** | Per-question agent traces, tool calls, latencies, token costs, eval scores | Storage / Obs | persistent, append-only |
| C18 | **Feature Store (lightweight)** | Per-IPO + per-day features used by forecaster — kept simple (Parquet on disk) for v1 | Storage | persistent |
| C19 | **Eval Harness** | Runs offline eval suites against gold sets; emits dashboard-ready reports | Cross-cutting | scheduled + pre-deploy |

**The single most important boundary:** C9–C13 (batch) NEVER call C3 (agent). The agent only ever *reads* from C14–C18. Batch pipelines fail loudly into C17 and surface in dashboards; they don't break user-facing flow.

---

## 3. Data Flow

### 3.1 End-to-end: from PDF on disk to cited+forecasted answer

```
                          ┌── BATCH (offline, hours-old freshness is fine) ──┐
                          │                                                   │
SEBI / BSE / NSE listings page                                                │
        │                                                                     │
        ▼ (C9) DRHP Ingestor — HTTP + scrape                                  │
   Object store: raw PDF + listing metadata                                   │
        │                                                                     │
        ▼ (C10) PDF Parser — Unstructured/Docling/PyMuPDF                     │
   Object store: parsed JSON (sections, tables, page map)                     │
        │                                                                     │
        ▼ (C11) Chunker + Embedder                                            │
   Vector store: chunks w/ {ipo_id, section, page, parent_id}                 │
   Relational DB: IPO row, sections index                                     │
        │                                                                     │
        ▼ (C12) Historical IPO Scraper (independent track)                    │
   Relational DB: past_ipos, listing_ohlc, subscription_book                  │
        │                                                                     │
        ▼ (C13) Forecast Trainer — sklearn/statsmodels + conformal            │
   Object store: model_vX.pkl + calibration_set + backtest_report             │
        │                                                                     │
                          └────────────────────────────────────────────────────┘
                                          │
                                          ▼
                          ┌── ON-DEMAND (seconds matter) ──┐
                          │                                 │
User picks IPO + asks: "Is this overpriced vs peers?"      │
        │                                                   │
        ▼ (C2) API Gateway issues run_id, opens SSE         │
        ▼ (C3) Agent — LangGraph state machine              │
              │                                             │
              │ plan: needs (a) what DRHP says about        │
              │       pricing, (b) peer multiples,          │
              │       (c) historical comparable IPOs        │
              │                                             │
              ├─► (C4) Retriever  ───► Vector store         │
              │       returns: chunks from "Basis for       │
              │       Issue Price" + Financials             │
              │                                             │
              ├─► (C5) Peer Comparator ─► Relational DB     │
              │       returns: 5 listed peers + multiples   │
              │                                             │
              ├─► (C6) Extractor (cached) ─► JSON snapshot  │
              │                                             │
              ├─► (C7) Forecaster ─► loads model_vX         │
              │       returns: listing-day return p50, 80%, │
              │       95% intervals + feature attribution   │
              │                                             │
              ├─► (C8) Charter ─► peer bar chart + forecast │
              │       histogram                             │
              │                                             │
              ▼ synthesize: compose cited answer            │
              ▼ cite_check node: every claim has source?    │
                if NO → re-retrieve or drop claim           │
              ▼ emit final answer + chart specs             │
        │                                                   │
        ▼ (C17) write full trace + token costs              │
        │                                                   │
        ▼ Frontend renders: prose w/ inline cites,          │
          methodology pane, forecast chart, peer table      │
                          └─────────────────────────────────┘
```

### 3.2 Key invariants

- **Every assistant claim → at least one citation.** Enforced in the `cite_check` node, evaluated offline by the eval harness, surfaced in the UI.
- **The forecaster never sees the future.** Time-aware CV; features must be computable on `T-1` of listing day.
- **Extraction is cached.** First time an IPO is asked about, the Extractor runs and persists JSON to the relational DB. Subsequent runs read from cache. This protects latency and budget.
- **The agent reads only.** Tools have no side effects on user-visible state. Side effects (logging, caching) go to C17/C15 in append-only mode.

### 3.3 What's batch vs on-demand

| Concern | Mode | Why |
|---------|------|-----|
| DRHP discovery/download | Batch (daily) | New filings appear daily-ish; no need for real-time |
| PDF parsing | Batch (per-IPO, once) | Slow (~minutes per 400-page doc), deterministic, cacheable |
| Chunk + embed | Batch (per-IPO, once) | Embedding cost; idempotent |
| Historical IPO scrape | Batch (weekly) | Listing data is settled; weekly refresh is fine |
| Peer fundamentals refresh | Batch (weekly) | Quarterly results dominate; weekly is generous |
| Forecast model training | Batch (manual / quarterly) | Need stable training set + held-out backtest |
| Structured extraction | **Hybrid** — on-demand first time, cached thereafter | Heavy LLM cost; deterministic per DRHP |
| Agent run | On-demand | This is the product |
| Eval suite (offline) | Batch (pre-deploy + nightly) | Regression detection |
| Eval traces (online) | On-demand, persisted | Every prod run is a data point |

---

## 4. Where the "Agentic" Surface Lives

A common failure mode is making the entire system agentic. Don't.

- **Deterministic everywhere except C3 (Agent Orchestrator).** Even within C3, prefer the **LangGraph state-machine** style over freeform ReAct: planner → tool-loop (bounded iterations) → synthesize → cite-check, with explicit edges and termination conditions. This is what makes the system testable and observable, and it's the production pattern that holds up. ([LangGraph: Build Stateful Multi-Agent Systems](https://www.mager.co/blog/2026-03-12-langgraph-deep-dive/), [LangGraph vs ReAct](https://amitavroy.com/articles/2025-06-29-LangGraph-vs-ReAct-When-Should-You-Use-Which-for-Your-Next-AI-Agent))
- **Tools are dumb.** C4–C8 are plain Python functions wrapped as tools. They don't call the LLM (except C6 Extractor and *optionally* a reranker). They have type-signed inputs and outputs.
- **The agent doesn't compute features.** Forecaster (C7) loads a versioned model + computes features deterministically from C15/C18. The agent invokes it but never reasons about feature engineering at request time.
- **Cite-check is a code node, not an LLM call.** It validates that every span in the assistant output has at least one resolved source ID from the run's retrieved set. Cheap, deterministic, and aligns with the honesty-first framing.

---

## 5. DS Evaluation Hooks (the visibility surface)

Evaluation is not a sidecar; it's part of the architecture. Hook locations:

| Hook | Component(s) | Metric | Cadence |
|------|--------------|--------|---------|
| **H1: Retrieval quality** | C4 + C19 | recall@k, precision@k, MRR vs gold Q→passage labels | nightly + pre-deploy |
| **H2: Faithfulness / hallucination** | C3 output + C19 | Ragas faithfulness, citation-coverage (% claims with valid cite) | per-run online + nightly offline |
| **H3: Extraction accuracy** | C6 + C19 | field-level F1 vs hand-labeled gold (~30 DRHPs) | manual + on model change |
| **H4: Forecast performance** | C13 + C19 | time-series-CV MAE, sMAPE; conformal coverage; calibration (PIT histogram); baseline vs model | each training run |
| **H5: Agent operational** | C17 | success rate, p50/p95 latency, tools-per-run, token cost/run, failure taxonomy | always on |
| **H6: Drift** | C12 + C13 | population stability index on features, performance drift on rolling backtest | weekly |

These hooks emit to a single **Eval dashboard** (could be a static HTML report committed under `/eval-reports/` per release — cheap, very Data-Scientist-coded). The whole point is making the work *visible* to a hiring DS lead.

---

## 6. Recommended Project Structure

```
drhplens/
├── app/                              # C1+C2 — web app
│   ├── frontend/                     # Next.js (or Streamlit for ultra-fast v0)
│   │   ├── components/
│   │   │   ├── ChatPane.tsx
│   │   │   ├── CitationLink.tsx
│   │   │   ├── ForecastChart.tsx
│   │   │   └── PeerTable.tsx
│   │   └── pages/
│   └── api/                          # FastAPI
│       ├── main.py
│       ├── routes/{ipos.py,ask.py,runs.py,eval.py}
│       └── schemas.py
│
├── agent/                            # C3 — orchestration
│   ├── graph.py                      # LangGraph state machine definition
│   ├── nodes/{plan.py,tool_loop.py,synthesize.py,cite_check.py}
│   ├── prompts/                      # versioned; .md files
│   └── policies.py                   # max iterations, budget caps
│
├── tools/                            # C4–C8 — tool implementations
│   ├── retriever.py                  # hybrid retrieval + rerank
│   ├── peer_comparator.py
│   ├── extractor.py                  # LLM + regex + rules
│   ├── forecaster.py                 # loads model, computes features
│   └── charter.py
│
├── pipelines/                        # C9–C13 — batch pipelines
│   ├── ingest_drhp.py
│   ├── parse_pdf.py
│   ├── chunk_and_embed.py
│   ├── scrape_historical_ipos.py
│   ├── scrape_peer_fundamentals.py
│   └── train_forecaster.py
│
├── ml/                               # forecast modeling, isolated
│   ├── features.py                   # deterministic feature builders
│   ├── models/{baseline.py,gbm.py,linear.py}
│   ├── calibration.py                # conformal predictors
│   ├── backtest.py                   # time-aware CV
│   └── registry.py                   # versioned artifact loader
│
├── eval/                             # C19 — eval harness
│   ├── rag/{faithfulness.py,recall.py,citation.py}
│   ├── extraction/eval_f1.py
│   ├── forecast/{coverage.py,pit.py}
│   ├── gold/                         # hand-labeled gold sets (committed)
│   │   ├── qa_pairs.jsonl
│   │   ├── extraction_labels.jsonl
│   │   └── README.md
│   └── reports/                      # generated HTML dashboards
│
├── storage/                          # C14–C18 — clients & schemas
│   ├── vector.py                     # Qdrant / pgvector client
│   ├── db.py                         # SQLAlchemy models
│   ├── object_store.py               # S3/R2/MinIO/local
│   └── run_log.py                    # writes traces to LangSmith/Phoenix + Postgres
│
├── data/                             # local dev data (gitignored except samples)
├── notebooks/                        # exploratory; promoted to /eval or /ml on merit
├── scripts/                          # ops: backfill, retrain, eval-run
├── docker/                           # Dockerfiles + compose for dev stack
├── tests/                            # unit + integration
└── README.md                         # methodology-forward, like a paper
```

### Structure rationale

- **`app/` is thin**, a presentation/transport layer only. Swapping Next.js for Streamlit during early dev is cheap if the API surface is clean.
- **`agent/` separated from `tools/`** so an evaluator can read the agent logic in 50 lines without grepping through retrieval code.
- **`pipelines/` are scripts**, not services. Each is runnable as `python -m pipelines.X` and as a scheduled job. No Airflow for v1 — cron + Makefile is enough.
- **`ml/` is the DS portfolio surface.** This folder is what hiring managers will read. Keep it clean, with `features.py` deterministic and `backtest.py` honest.
- **`eval/gold/` is committed.** Reviewers can re-run evals locally. This is the single most credibility-increasing folder in the repo.
- **`storage/` centralizes I/O.** No tool or pipeline touches a database client directly; they go through these adapters. This is what enables swapping pgvector → Qdrant later without touching the agent.

---

## 7. Architectural Patterns

### Pattern 1: Structure-aware chunking with parent-document retrieval

**What:** Parse DRHPs into a section tree (`Risk Factors`, `Industry Overview`, `MD&A`, `Financial Statements`, `RPTs`, `Use of Proceeds`, ...). Chunk *within* sections; store each leaf chunk with a pointer to its parent section. At retrieval time, fetch leaf chunks then expand to parent context as needed.

**Why for DRHPs:** Section boundaries are deeply semantic in prospectuses — a sentence in "Risk Factors" means something very different from the same sentence in "Industry Overview". Layout-aware chunking outperforms fixed-token chunking for financial documents. ([Snowflake Engineering — Long-Context Isn't All You Need](https://www.snowflake.com/en/engineering-blog/impact-retrieval-chunking-finance-rag/), [Hierarchical Text Segmentation Chunking](https://arxiv.org/pdf/2507.09935))

**Trade-offs:** Higher upfront parser complexity. Worth it: section metadata is also what enables filtered retrieval ("only retrieve from Risk Factors") which is a giant precision win for an agent.

### Pattern 2: Hybrid retrieval (BM25 + dense + rerank) with metadata filters

**What:** Combine BM25 (keyword) and dense (embedding) search, then cross-encoder rerank top-K. Always filter by `ipo_id` (and optionally `section`) before scoring.

**Why:** DRHPs contain a lot of named entities, regulations, and exact phrases ("Schedule VI", "Regulation 26(1)") where BM25 dominates. They also contain semantic claims where dense wins. Reranking is the cheapest precision boost available.

**Trade-off:** Three retrieval calls per query. Fine on-demand; cache reranker outputs per (query-hash, ipo_id).

### Pattern 3: Conformal prediction over a calibrated forecaster

**What:** Train a point-estimate forecaster (GBM / regularized linear) for listing-day return. Wrap it with a split-conformal predictor calibrated on a held-out post-2022 set to yield 80%/95% intervals with guaranteed marginal coverage.

**Why:** The honesty-first framing demands calibrated uncertainty, not a single number. Conformal gives you coverage guarantees without distributional assumptions — exactly what a Data Scientist audience wants to see and what a retail user needs to interpret responsibly.

**Trade-off:** Slightly wider intervals than a parametric Bayesian model would give if its assumptions hold. Worth it for honesty + simplicity.

### Pattern 4: State-machine agent (not freeform ReAct)

**What:** Use LangGraph (or equivalent) to model the agent as `plan → tool_loop[bounded] → synthesize → cite_check`. Explicit edges, explicit state, bounded iterations.

**Why:** Predictability, observability, and the ability to insert non-LLM nodes (like `cite_check`). The state graph is the documentation of the agent's reasoning shape. ([LangGraph](https://www.langchain.com/langgraph), [LangGraph vs ReAct](https://amitavroy.com/articles/2025-06-29-LangGraph-vs-ReAct-When-Should-You-Use-Which-for-Your-Next-AI-Agent))

**Trade-off:** Slightly more upfront code than a `create_react_agent(...)` one-liner. Returns the investment within days as soon as you need to debug a failure.

### Pattern 5: Storage as the integration bus

**What:** Components communicate through stores (vector, relational, object, run-log), not through each other. Batch pipelines write; on-demand tools read.

**Why:** Single-developer + portfolio piece + future v2 reuse. Avoids the complexity tax of inter-service APIs while still respecting clear boundaries. Lets you re-process a DRHP without restarting the agent.

**Trade-off:** Eventual consistency for newly ingested IPOs (must wait for embed job). Acceptable — there's no real-time IPO ingestion need.

### Pattern 6: Eval-by-default

**What:** Every agent run writes a full trace + tool call list + token cost to C17. The eval harness can replay any run against newer prompts/models for regression testing.

**Why:** Makes the project's *DS rigor* visible. Production traces become training/eval data for the next iteration. ([Arize Phoenix RAG eval](https://arize.com/docs/phoenix/cookbook/evaluation/evaluate-rag), [LangSmith](https://www.langchain.com/langsmith))

**Trade-off:** Storage cost (trivial at portfolio scale) and a discipline tax to always log structured rather than unstructured.

---

## 8. Build Order (Dependency-Driven)

The right order is to build the **thinnest possible vertical slice** first, then add depth in horizontal layers. Below is the build sequence keyed to component IDs.

### Stage 0 — Skeleton (gets things runnable)
0.1. Repo scaffolding, `storage/` adapters with local-first defaults (SQLite + pgvector or LanceDB + local FS).
0.2. FastAPI hello-world and frontend hello-world (could be Streamlit until late).
0.3. CI: lint + tests + a smoke pipeline.

### Stage 1 — Vertical slice MVP (ONE IPO, ONE question type, full citation loop)
**Goal:** Answer "What does this DRHP say about [topic]?" for a single hardcoded IPO, with citations.

1.1. **C9 (manual)** — download 1 DRHP PDF by hand into the object store.
1.2. **C10** — basic PDF parser (PyMuPDF or Unstructured, no fancy section detection yet).
1.3. **C11** — naive recursive chunker + embedding + vector upsert.
1.4. **C4** — retriever (vector-only is fine; BM25 later).
1.5. **C3** — minimal LangGraph: retrieve → synthesize → cite_check.
1.6. **C2 + C1** — `/ask` endpoint + Streamlit chat with citation rendering.
1.7. **H2 (light)** — manual eyeball check on 10 questions.

**Ship moment:** End of Stage 1 — you have a demoable RAG product with cited answers. This is already 60% of the portfolio signal.

### Stage 2 — Extraction + multi-IPO
**Goal:** Multiple IPOs in the catalogue, structured signal extraction visible in the UI.

2.1. **C9 (automated)** — DRHP discovery from SEBI/BSE.
2.2. **C10 (upgraded)** — section-aware parser; tag chunks with section.
2.3. **C11 (upgraded)** — structure-aware chunking + parent-doc pointers.
2.4. **C6** — Structured Extractor (LLM + rules).
2.5. **eval/gold/extraction_labels.jsonl** — hand-label 20–30 DRHPs.
2.6. **H3** — extraction F1 eval pipeline.
2.7. UI: IPO picker + extraction summary card.

### Stage 3 — Historical IPO data + peer comparator
**Goal:** Peer-comparison answers.

3.1. **C12** — scraper for past mainboard IPOs (BSE/NSE/yfinance/screener).
3.2. **C15** — relational schema for IPOs, peers, prices.
3.3. **C5** — Peer Comparator tool.
3.4. UI: peer table component.

### Stage 4 — Forecaster
**Goal:** Calibrated listing-day forecast.

4.1. **ml/features.py** — feature builders deterministic from C15/C18.
4.2. **ml/models/baseline.py** — sector median + size baseline (CRITICAL: never skip the baseline; it's the honesty benchmark).
4.3. **ml/models/gbm.py** — actual model.
4.4. **ml/calibration.py** — conformal wrapper.
4.5. **ml/backtest.py** — time-aware CV.
4.6. **C13** — training pipeline + artifact registry.
4.7. **C7** — Forecaster tool.
4.8. **H4** — coverage + PIT + MAE dashboard.
4.9. UI: forecast chart + methodology pane.

### Stage 5 — Eval & polish
**Goal:** The DS rigor surface.

5.1. **eval/gold/qa_pairs.jsonl** — 50–100 hand-labeled Q→passage pairs.
5.2. **H1** — Ragas retrieval evals.
5.3. **H2** — Ragas faithfulness + citation-coverage online.
5.4. **H5** — agent operational dashboards (latency, cost, failure taxonomy).
5.5. **eval/reports/** — committed HTML dashboards per release.
5.6. Methodology pane in UI: links to eval reports.

### Dependency graph (one-shot view)

```
C9 ──► C10 ──► C11 ──► C14
                       │
                       └─► C4 ─┐
                               │
C12 ──► C15 ──► C5 ────────────┤
                               │
C15 ──► ml/features ──► C13 ──► C7 ──┤
                                     ├──► C3 ──► C2 ──► C1
C6 ─► C15 (cache) ───────────────────┤
                                     │
C8 ──────────────────────────────────┘

C17 ◄── every component writes traces
C19 ◄── reads from C14/C15/C17 + gold sets
```

### Vertical-slice MVP opportunities (explicit)

- **MVP-A "Cited Q&A on one IPO"** = C9-manual + C10-basic + C11-basic + C4 + C3 + C2 + C1. **Ship in days, not weeks.** Already differentiates from "ChatGPT pasted a DRHP".
- **MVP-B "Cited Q&A + Extraction"** = MVP-A + C6 + extraction eval gold. Adds the structured-extraction story that ML signal hangs on.
- **MVP-C "Cited Q&A + Peer table"** = MVP-A + C12 + C5. Adds the data-engineering signal.
- **MVP-D "The full DRHPLens v1"** = all of the above + C7 forecaster + full eval harness.

**Recommendation:** Ship MVP-A publicly (even just a Loom + repo). Iterate to MVP-D in 4 stages, each its own roadmap phase, each independently shippable.

---

## 9. Scaling Considerations

This is a portfolio piece — true scale concerns are secondary, but a DS interviewer *will* ask. Honest answers below.

| Scale | Reality | Adjustments |
|-------|---------|-------------|
| Portfolio demo (1–10 concurrent) | Default | Single FastAPI process, SQLite + pgvector or local Qdrant, free-tier LLM/embedding APIs. |
| Hundreds of concurrent | Plausible if Hacker-News'd | Postgres + managed vector store, LLM API rate-limit handling, per-IPO extraction cache becomes critical, move to a queue (Redis/RQ) for batch jobs. |
| Thousands+ | v2 SaaS territory | Split agent runtime from API gateway, dedicated retrieval service, model server (BentoML/Modal), proper job orchestrator (Prefect/Dagster), per-tenant data isolation. |

### Scaling priorities (what breaks first, in order)

1. **LLM API rate limits + cost** — solved by caching extraction (C6), caching reranker outputs, and using small models for cheap nodes (cite_check, planner).
2. **PDF parsing throughput** — 400-page parses are slow. Solve by parallelism + persistent cache before parallelism.
3. **Vector store recall at >10k documents** — solve with metadata filtering (already in design) before sharding.
4. **Eval dataset staleness** — at the portfolio stage, the eval *gold set* is the bottleneck to model improvement. Budget time for it.

---

## 10. Anti-Patterns

### Anti-Pattern 1: Making the whole system agentic

**What people do:** Wrap ingestion, scraping, and even chunking in LLM calls "for flexibility".
**Why it's wrong:** Non-deterministic batch pipelines are unfixable. They will fail silently and corrupt the index.
**Do instead:** Pure-Python deterministic pipelines. The LLM gets to participate in C3 (agent) and C6 (extractor, where it's cached). Nowhere else.

### Anti-Pattern 2: Forecasting without a baseline

**What people do:** Train GBM/XGBoost, report MAE, ship.
**Why it's wrong:** A Data Scientist reviewer will instantly ask "vs what?" — and if the GBM doesn't beat sector-median + issue-size, you don't have a model, you have a fitted curve.
**Do instead:** Build `baseline.py` *first*. Report deltas. Make beating baseline a release gate.

### Anti-Pattern 3: Citations without verification

**What people do:** Have the LLM emit `[1]`, `[2]`, `[3]` style citations in prose and call it cited.
**Why it's wrong:** LLMs cheerfully invent citation numbers. This collapses the entire honesty-first framing.
**Do instead:** `cite_check` node validates every citation against the retrieved set. Unsupported claims are either re-retrieved or removed. Citation coverage is a top-level metric (H2).

### Anti-Pattern 4: Coupling chunking to a specific embedding model

**What people do:** Hardcode chunk size and overlap based on one embedding model's context window.
**Why it's wrong:** Re-embedding is cheap; re-parsing 500-page DRHPs is not. You will want to swap embedding models.
**Do instead:** Parsed-JSON in object store is the durable artifact. Chunking + embedding is a re-runnable transform downstream.

### Anti-Pattern 5: Treating evals as a final-week task

**What people do:** Build the system, then "add evals" in the last sprint.
**Why it's wrong:** Without evals you have no feedback loop and you'll ship regressions. You also won't have the visible artifacts that make this a DS portfolio piece.
**Do instead:** Build gold sets *concurrently* with each component. The 30 hand-labeled DRHPs for extraction eval can be built in a weekend; don't defer.

### Anti-Pattern 6: One giant prompt for the agent

**What people do:** Stuff retrieval + reasoning + citation + formatting + safety into one system prompt.
**Why it's wrong:** Unobservable, untestable, and the cite-check problem can't be solved this way.
**Do instead:** Multiple small prompts at multiple LangGraph nodes. Versioned in `agent/prompts/*.md`. Tested individually.

### Anti-Pattern 7: Hiding the model from the user

**What people do:** Present the forecast as a single number with no methodology.
**Why it's wrong:** Violates honesty-first framing AND under-sells the DS work.
**Do instead:** Methodology pane in the UI: model version, training window, backtest MAE, coverage achieved, top features. This *is* the portfolio piece.

---

## 11. Integration Points

### External services / data sources

| Source | Integration | Notes / Gotchas |
|--------|-------------|-----------------|
| SEBI public filings | HTTP scrape + PDF download | Inconsistent URL schemes; expect HTML changes. Build a tolerant ingestor with retries. |
| BSE/NSE IPO history pages | HTTP scrape | NSE has anti-scraping; rotate UAs + slow rate. BSE is friendlier. |
| screener.in (peer fundamentals) | HTTP scrape | ToS-respect: low rate, cache aggressively, attribute. |
| yfinance (`.NS`/`.BO`) | Python lib | Sometimes drops listing-day data; cross-check with NSE/BSE. |
| Company IR pages | Manual + scrape (best-effort) | Used for peer mapping fallback. Treat as MEDIUM-confidence. |
| LLM API (OpenAI/Anthropic/local) | HTTPS + Python SDK | Rate-limit aware; embed responses + extraction in cache. Defer model choice to STACK.md. |
| Embedding API (or local model) | HTTPS or local | Decide based on document volume + cost. Local `bge`/`e5` is competitive. |
| Observability (LangSmith / Phoenix) | SDK + HTTP | Optional but recommended; OSS Phoenix is fine for portfolio. ([Arize Phoenix](https://arize.com/docs/phoenix/cookbook/evaluation/evaluate-rag)) |

### Internal boundaries

| Boundary | Mechanism | Notes |
|----------|-----------|-------|
| Frontend ↔ API | HTTP/JSON + SSE for streaming | SSE lets the UI render tool calls as they happen — huge UX win. |
| API ↔ Agent | In-process function call (v1) | Becomes a queue boundary at the scale section above. |
| Agent ↔ Tools | Tool-calling protocol (LangGraph nodes) | Each tool has Pydantic schema for inputs/outputs. |
| Tools ↔ Storage | Adapters in `storage/` | Single chokepoint; testable; swappable. |
| Batch pipelines ↔ Storage | Direct writes | Idempotent; safe to re-run; each pipeline has `--reprocess` flag. |
| Eval ↔ everything | Read-only via `storage/` + `run_log` | Eval never mutates state. |
| Run log ↔ rest | Append-only writes | Never read by user-facing flow; only by eval + dashboards. |

---

## 12. Notes for Roadmap Authoring

For the orchestrator stitching this into a roadmap:

- **Phase 1 should be MVP-A (single-IPO cited Q&A).** Concrete, ships fast, demonstrably differentiated. C1+C2+C3+C4 + manual C9/C10/C11 for one document.
- **Phase 2 should add the extraction + multi-IPO pipeline** (C9 automation, C10 upgrade, C11 upgrade, C6, gold-labeling task). This is where the *NLP DS signal* lands.
- **Phase 3 should add historical IPO data + peer comparator** (C12, C15, C5). This is where the *data-engineering signal* lands.
- **Phase 4 is the forecaster** (full `ml/` folder, C13, C7). This is where the *modeling DS signal* lands — the headline portfolio output. Allocate accordingly: this phase is the riskiest and most differentiating.
- **Phase 5 is the eval + polish pass.** Some evals exist from earlier phases; this phase makes them dashboard-quality and surfaces them in the UI methodology pane.
- **Cross-cutting throughout:** C17 run log + `storage/` adapters must be solid by end of Phase 1; everything else depends on them.

The vertical-slice pattern (small but end-to-end) at each phase ensures every phase ships something demoable — critical for a portfolio project where momentum matters more than completeness.

---

## Sources

### High-confidence (used to ground specific recommendations)

- [LangGraph: Build Stateful Multi-Agent Systems That Don't Crash — Mager.co (2026)](https://www.mager.co/blog/2026-03-12-langgraph-deep-dive/)
- [LangGraph vs ReAct: When Should You Use Which? — Amitav Roy (2025)](https://amitavroy.com/articles/2025-06-29-LangGraph-vs-ReAct-When-Should-You-Use-Which-for-Your-Next-AI-Agent)
- [LangGraph — Agent Orchestration Framework (official)](https://www.langchain.com/langgraph)
- [Long-Context Isn't All You Need: How Retrieval & Chunking Impact Finance RAG — Snowflake Engineering](https://www.snowflake.com/en/engineering-blog/impact-retrieval-chunking-finance-rag/)
- [Enhancing Retrieval Augmented Generation with Hierarchical Text Segmentation Chunking (arXiv 2507.09935)](https://arxiv.org/pdf/2507.09935)
- [Metadata-Driven Retrieval-Augmented Generation for Financial Question Answering (arXiv 2510.24402)](https://arxiv.org/pdf/2510.24402)
- [Rethinking Retrieval: From Traditional RAG to Agentic and Non-Vector Reasoning in Finance (arXiv 2511.18177)](https://arxiv.org/pdf/2511.18177)
- [Evaluate RAG — Arize Phoenix](https://arize.com/docs/phoenix/cookbook/evaluation/evaluate-rag)
- [Observability Tools — Ragas](https://docs.ragas.io/en/v0.3.5/howtos/observability/)

### Medium-confidence (ecosystem context)

- [What Is Agentic RAG? From LLM RAG to AI Agents — Weaviate](https://weaviate.io/blog/what-is-agentic-rag)
- [Agentic RAG: Architecture, Use Cases, and Limitations — Vellum](https://www.vellum.ai/blog/agentic-rag)
- [The Complete Guide to RAG Architectures: From Naive to Agentic — Medium](https://atul4u.medium.com/the-complete-guide-to-rag-architectures-from-naive-to-agentic-c90c8a87cf56)
- [Building Hierarchical Agentic RAG Systems — InfoQ](https://www.infoq.com/articles/building-hierarchical-agentic-rag-systems/)
- [From MLOps to ML Systems with Feature/Training/Inference Pipelines — Hopsworks](https://www.hopsworks.ai/post/mlops-to-ml-systems-with-fti-pipelines)

---
*Architecture research for: DRHPLens (agentic-RAG over Indian IPO DRHPs + listing-day forecaster + DS-rigorous eval)*
*Researched: 2026-05-28*
