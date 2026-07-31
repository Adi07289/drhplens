# Spike Conventions

Patterns and pins established across the Phase 6.1 eval-harness spikes. New spikes/build follow these unless the question requires otherwise.

## Stack

- Python via the project `.venv` (3.11.15). Run experiments as `PYTHONPATH=. .venv/bin/python`.
- Load secrets with `set -a && . ./.env && set +a` (never print values). Keys present: `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST`.
- These are "facts not feelings" spikes → CLI/stdout verification (version pins, does-it-attach, benchmark numbers), no UI.

## Pins (validated live)

| Package | Pin | Why |
|---------|-----|-----|
| langfuse | **`<3` (2.60.10)** | v4 (4.14.1) is a full OTEL rewrite of all 3 obs files + still needs `langchain`; buys nothing 6.1 needs. |
| deepeval | **`>=4.1,<5` (4.1.4)** | native `GeminiModel` judge, no OpenAI dep. |
| ragas | offline only (`>=0.4,<0.5`) | flag-gated cross-check; never in CI. |

## Judge / model

- **LLM judge model = `gemini-3.5-flash`** (the codebase standard). NOT `gemini-2.5-flash` — it 404s ("no longer available to new users").
- Free-tier Gemini = **5 RPM** → any judge fan-out needs `async_mode=False` + serial + `tenacity` backoff (~30–65s) + DeepEval cache (`-c`).

## Langfuse instrumentation pattern

- Instrument via the **direct client API** (`lf.trace(name, metadata=…, tags=…)` → `trace.score(name, value, comment)` → `lf.flush()`), NOT the LangChain `CallbackHandler` (needs the `langchain` package on v2 AND v4; repo has only `langchain_core`).
- `lf.flush()` before process exit is mandatory in short-lived runners/CI or scores never ship.
- Preserve the `is_enabled()` no-op fallback: keys unset → agent runs unchanged.

## Eval-metric patterns

- Compute **recall@k over `retrieved_chunks` (50 Qdrant candidates)**, not `reranked_top_k` (capped at `RERANK_TOP_K=5`).
- Recall is **saturated (1.00)** on the current gold set (coarse 10–101-page `expected_sources`) → treat `recall@10 ≥ 0.85` as a labelled regression floor, not a quality headline (P10). Tighten gold spans to make it discriminate.
- Retrieval path (`retrieve.run` + `rerank.run`) runs with no Gemini call — use it for retrieval metrics to avoid the RPM limit.
