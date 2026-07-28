# Spike Manifest

## Idea

Phase 6.1 (alias "6a") eval-harness — validate the three riskiest unknowns from `06.1-AI-SPEC.md` before planning: (1) the Langfuse v2→v4 API migration for trace enrichment + custom scores, (2) DeepEval faithfulness on a native Gemini judge (no OpenAI), and (3) the real recall@k baseline that ratifies the `recall@10 ≥ 0.85` hard-gate threshold. Goal = decisions + confidence, not production code.

## Requirements

Design decisions locked upstream (SPEC/AI-SPEC/UI-SPEC on branch `phase6/6a-eval-harness`), non-negotiable for the real build:

- DeepEval faithfulness is REPORTED (≥0.95 target), never a CI gate; deterministic recall@k + citation-accuracy are HARD-GATED. Report + gate share one `eval/metrics/` impl.
- Langfuse enrichment must preserve the no-op fallback (keys unset → agent runs unchanged).
- Honesty invariant: no live judge call at page render; committed `eval_summary.json` only.
- **[001] Pin `langfuse<3` (2.60.10) for 6.1** — v4 is a full OTEL rewrite + still needs `langchain`; buys nothing 6.1 needs.
- **[001] Instrument Langfuse via the direct client API** (`lf.trace()`/`trace.score()`/`create_score`), NOT the LangChain CallbackHandler (which needs the `langchain` package on v2 AND v4; repo has only `langchain_core`).
- **[001] ⚠ EVAL-05 = "make tracing actually work + enrich"** — the callback handler has been silently no-op (no `langchain`), so traces may not have been captured; plan must size the direct-API instrumentation, not just enrichment.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | langfuse-v4-migration | standard | v4 custom-score + cost/latency/tool-call attach + no-op fallback → migrate vs pin<3 | ✓ VALIDATED (pin<3 + direct API; langchain-gap caveat) | langfuse, observability, EVAL-05 |
| 002 | deepeval-gemini-judge | standard | FaithfulnessMetric.measure() on native GeminiModel (no OpenAI) + assert_test opt-in → confirm pin | PENDING | deepeval, faithfulness, gemini |
| 003 | recall-baseline | standard | real recall@5/10/30 over the 13-Q Swiggy gold set → ratify recall@10 ≥0.85 gate | PENDING | recall, retrieval, gate-threshold |
