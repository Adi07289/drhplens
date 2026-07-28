# Deferred Items — Phase 06.1

Out-of-scope discoveries logged during execution. NOT fixed by the plan that found them.

## From 06.1-03 (Langfuse direct-API trace enrichment)

- **`tests/integration/test_agent_e2e.py::test_grounded_question_returns_cited_answer` — live Gemini API network timeout (>60s).**
  - Discovered during: 06.1-03 full-suite regression run.
  - Root cause: the `generate` node's live Gemini LLM call (`agent/nodes/generate.py:215` → instructor → `google.genai` → httpx SSL read) exceeded the 60s `pytest-timeout` on this run. This is an external-network flake against the Gemini API, executing inside `GRAPH.invoke` **before** any of 06.1-03's trace-emission code runs.
  - Why out of scope: not caused by 06.1-03 changes (which touch only `trace_enrichment.py`, `graph.invoke_with_tracing` wrapping, and `test_langfuse_trace.py`). The failing frame is unmodified live-service code. The rest of the suite (588 tests) passes.
  - Suggested owner: whoever runs the live e2e lane — retry, or move this test behind a `--run-eval`/live-network gate so it does not fail the default suite on Gemini latency.
