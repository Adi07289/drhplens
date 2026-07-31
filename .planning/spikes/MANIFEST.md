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
- **[002] Pin `deepeval>=4.1,<5` (4.1.4); judge = native `GeminiModel`** (no OpenAI dep).
- **[002] Judge model = `gemini-3.5-flash`, NOT `gemini-2.5-flash`** (2.5-flash 404s "no longer available"; 3.5-flash is the codebase standard) — correct the AI-SPEC + CLAUDE.md.
- **[002] ⚠ Free-tier Gemini = 5 RPM** for gemini-3.5-flash; faithfulness fan-out exhausts it → runner needs async_mode=False + serial + tenacity backoff + DeepEval cache; a full faithfulness pass is minutes. Reinforces report-not-gate + ≥0.7 human calibration.
- **[003] Compute recall@10/@30 over `retrieved_chunks` (50), NOT `reranked_top_k`** (RERANK_TOP_K=5 caps k>5).
- **[003] ⚠ recall is SATURATED at 1.00** — gold `expected_sources` are 10–101-page section ranges (mean 44.5); span-overlap is trivially satisfied. Keep `recall@10 ≥ 0.85` as a labelled regression FLOOR only, never a headline quality metric (P10). Real signal = citation-accuracy + faithfulness.
- **[003] Gold-set task:** tighten `expected_sources` to specific answer page(s) (≤2–3 pp) so recall discriminates; then re-ratify the threshold. Pairs with the RPT/numeric coverage gap.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | langfuse-v4-migration | standard | v4 custom-score + cost/latency/tool-call attach + no-op fallback → migrate vs pin<3 | ✓ VALIDATED (pin<3 + direct API; langchain-gap caveat) | langfuse, observability, EVAL-05 |
| 002 | deepeval-gemini-judge | standard | FaithfulnessMetric.measure() on native GeminiModel (no OpenAI) + assert_test opt-in → confirm pin | ✓ VALIDATED (deepeval 4.1.4; judge=gemini-3.5-flash; 5 RPM free-tier) | deepeval, faithfulness, gemini |
| 003 | recall-baseline | standard | real recall@5/10/30 over the 13-Q Swiggy gold set → ratify recall@10 ≥0.85 gate | ⚠ PARTIAL (recall=1.00 but SATURATED — coarse gold spans; keep as floor only) | recall, retrieval, gate-threshold, P10 |
