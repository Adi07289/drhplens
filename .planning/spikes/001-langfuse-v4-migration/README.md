---
spike: 001
name: langfuse-v4-migration
type: standard
validates: "Given the v2 app/observability/ code, when langfuse v4 is installed, then a custom score + cost/latency/tool-call metadata attach to a trace (with flush) AND the no-op fallback holds — decide migrate vs pin<3"
verdict: VALIDATED
related: []
tags: [langfuse, observability, EVAL-05]
---

# Spike 001: Langfuse v4 Migration (migrate vs pin)

## What This Validates

Given the v2-era `app/observability/` code, when we install the current langfuse SDK, can we still attach cost/latency/tool-call metadata + a failure-mode **custom score** to a trace and preserve the no-op fallback — and should Phase 6.1 **migrate to v4** or **pin `langfuse<3`**?

## Research (run live, not just docs)

| Question | Evidence (measured) |
|----------|---------------------|
| Latest langfuse | **4.14.1** (v4, OpenTelemetry SDK) |
| v2 API on v4? | **Gone.** `langfuse.callback.CallbackHandler`, `langfuse.decorators.langfuse_context` → `ModuleNotFoundError`. `client.score(trace_id=…)` → replaced by `client.create_score(*, name, value, trace_id=…, data_type=…)`. |
| v4 LangChain handler | `langfuse.langchain.CallbackHandler` — import fails: **`pip install langchain` required** (repo has only `langchain_core 1.4.0`). |
| v4 span API | Full OTEL redesign: `start_as_current_observation(as_type="span")`, `create_score`, `score_current_trace`. Trace-level metadata setter is non-obvious — two plausible calls (`span.update_trace`, `client.start_span`) both `AttributeError`. Non-trivial rewrite of all 3 obs files. |
| langfuse<3 install | **2.60.10** installs clean; all 3 `app/observability/` modules import OK. |
| v2 direct attach → Cloud | **Works.** `lf.trace(name, metadata=…, tags=…)` + `trace.score(name, value, comment)` + `lf.flush()` attached a real trace to Langfuse Cloud (id `dbedbe8d-c6a8-4759-8c33-b3e93d220703`). |

## How to Run

```bash
set -a && . ./.env && set +a
.venv/bin/pip install "langfuse<3"        # 2.60.10
.venv/bin/python -c "from app.observability.langfuse_client import get_client; \
  lf=get_client(); t=lf.trace(name='probe', metadata={'cost_usd':0,'latency_ms':1234,'tool_calls':3}, tags=['x']); \
  t.score(name='failure_mode', value=1, comment='retrieval_miss'); lf.flush(); print(t.id)"
```

## Investigation Trail

1. Installed langfuse latest → **4.14.1**. Confirmed the AI-SPEC's flag: the entire v2 import surface is removed; `get_client` / `Langfuse` / `create_score` are the v4 entry points.
2. Tried to attach a v4 trace → the OTEL span API differs from every guess (`start_as_current_span`, `start_span`, `span.update_trace` all `AttributeError`); scores (`create_score` / `score_current_trace`) exist and don't error, but setting **trace-level metadata** is non-obvious. Verdict: v4 = a genuine OTEL rewrite of all three obs files.
3. `langfuse.langchain.CallbackHandler` needs the **full `langchain` package** — not installed (only `langchain_core`).
4. Pinned `langfuse<3` → 2.60.10. All 3 obs modules import; `is_enabled()` True.
5. **SURPRISE (the load-bearing finding):** `get_callback_handler()` returned `_NoOpCallbackHandler` *with keys set* — langfuse printed `Could not import langchain. The langchain integration will not work.` The existing code does `from langfuse.callback import CallbackHandler` inside a `try/except ImportError → no-op`. Since `langchain` was never installed, **the callback-based tracing has been silently no-op — LangGraph runs likely have NOT been writing Langfuse traces via `invoke_with_tracing`**, on v2 *or* v4.
6. Proved the escape hatch: the **direct client API** (`lf.trace()` / `trace.score()` / `create_score()`) attaches metadata + custom scores to Cloud **without** `langchain` installed.

## Results

**Verdict: VALIDATED — with a critical, version-independent caveat.**

- **DECISION — pin `langfuse<3` (2.60.10) for Phase 6.1.** v4 is a full OTEL/span rewrite of all three obs files *and still needs `langchain`*; it buys nothing 6.1 requires. Pinning keeps the working code + no-op fallback and defers the OTEL migration to a dedicated later slice. Add `langfuse<3` to `requirements.txt`/`pyproject.toml`.
- **DECISION — instrument via the direct client API, not the LangChain CallbackHandler.** The callback handler needs the `langchain` package (v2 **and** v4). Attaching cost/latency/tool-call metadata + the `retrieval_miss/cite_check_fail/judge_flag/crash` custom scores through `lf.trace()`/`trace.score()` works today with zero new deps. (If callback-based auto-instrumentation is later wanted, add `langchain` explicitly — but it is not needed for EVAL-05.)
- **⚠ PLANNER-CRITICAL:** verify whether production Langfuse tracing has been live at all. The `get_callback_handler → _NoOpCallbackHandler` fallback means the cross-cutting "every agent run writes a full trace from day one" invariant may not have held in practice. EVAL-05 is therefore **"make tracing actually work (direct API) + enrich,"** not just "enrich existing traces." Size this in the plan.
- `flush()` before process exit is mandatory (short-lived runner/CI) — confirmed; without it scores never ship.
- No-op fallback preserved: `is_enabled()` gates on keys; with keys unset the agent runs unchanged.
