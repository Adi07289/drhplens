---
title: DRHPLens
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: streamlit
sdk_version: 1.36.0
app_file: app.py
pinned: false
license: mit
sleep_time: 1800
---

# DRHPLens

DRHPLens reads prospectuses for you. It cites what the document says and shows historical context. Decisions about investing are yours. This is not investment advice.

## What it does

- Answers plain-English questions about the Swiggy IPO DRHP (Phase 1 scope — one IPO)
- Every claim is backed by a span-level citation to the exact page in the prospectus
- Refuses to answer questions the document cannot support (Gate 1 + Gate 2 refusal posture)
- Three disclaimer surfaces: first-use modal, persistent footer, per-answer footer
- Mobile-responsive at 375px (recruiter demo on phone works)

## Methodology summary

DRHPLens uses LangGraph for agent orchestration, LlamaIndex + Docling for PDF ingestion, Qdrant + BAAI/bge-m3 for hybrid retrieval, BAAI/bge-reranker-v2-m3 for reranking, and Gemini 2.5 Flash + Instructor for structured answer generation. Every claim passes a non-LLM deterministic cite-check (fuzzy token overlap + numeric subset check) before reaching the user. Agent traces carry `claim_id` references for every claim from day one — these power the methodology pane in Phase 3. See the [/methodology](/methodology) page for full details.

## Roadmap

See [TODOS.md](./TODOS.md) for the deferred feature backlog.

- **Phase 2** — Multi-IPO catalogue (5-10 DRHPs; dynamic IPO selector; section-type filters)
- **Phase 3** — Methodology pane (show-your-work traces; numeric faithfulness eval gate EVAL-03)
- **Phase 4** — Peer-comparison engine (listed-peer fundamentals; screener.in + yfinance)
- **Phase 5** — Listing-day forecast (XGBoost + MAPIE conformal intervals; backtested on 50+ IPOs)
- **Phase 6** — Production hardening (EVAL-01 release gate; LAND-01 recruiter landing page; FAILGAL-01 live failure gallery)

## Run locally

```bash
uv pip install -e ".[dev]"
cp .env.example .env   # fill in your own keys (see .env.example for sources)
streamlit run app.py
```

Required env vars are documented in [.env.example](./.env.example).

## License

MIT
