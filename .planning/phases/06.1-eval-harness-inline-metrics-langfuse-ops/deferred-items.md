# Deferred Items — Phase 06.1

Out-of-scope discoveries logged during execution. NOT fixed by the plan that found them.

## From 06.1-03 (Langfuse direct-API trace enrichment)

- **`tests/integration/test_agent_e2e.py::test_grounded_question_returns_cited_answer` — live Gemini API network timeout (>60s).**
  - Discovered during: 06.1-03 full-suite regression run.
  - Root cause: the `generate` node's live Gemini LLM call (`agent/nodes/generate.py:215` → instructor → `google.genai` → httpx SSL read) exceeded the 60s `pytest-timeout` on this run. This is an external-network flake against the Gemini API, executing inside `GRAPH.invoke` **before** any of 06.1-03's trace-emission code runs.
  - Why out of scope: not caused by 06.1-03 changes (which touch only `trace_enrichment.py`, `graph.invoke_with_tracing` wrapping, and `test_langfuse_trace.py`). The failing frame is unmodified live-service code. The rest of the suite (588 tests) passes.
  - Suggested owner: whoever runs the live e2e lane — retry, or move this test behind a `--run-eval`/live-network gate so it does not fail the default suite on Gemini latency.

## From 06.1-05 (deterministic eval release gate)

- **`tests/eval/test_faithfulness_deepeval.py::test_faithful_fixture_assert_test_optin` — live Gemini free-tier 429 quota exhaustion.**
  - Discovered during: 06.1-05 full-suite regression run (`pytest -q --ignore=tests/integration/test_agent_e2e.py`).
  - Root cause: this opt-in test issues a real DeepEval `FaithfulnessMetric` LLM-judge call to `gemini-3.5-flash` (5 RPM / 20-per-day free tier, spike 002). Its skip-guard catches `RESOURCE_EXHAUSTED`/`429`/`quota` in the exception message; on this run a differently-worded rate-limit/degraded-response error slipped past the substring match and surfaced as a FAIL. Run in isolation the same test SKIPS cleanly (429 caught).
  - Why out of scope: 06.1-05 touches only `agent/policies.py` (2 additive gate constants), `scripts/release_gate.py` (a pure offline deterministic gate), and `tests/eval/test_release_gate.py` (offline fixtures). None import or affect the faithfulness_deepeval live path. The deterministic-gate work is fully offline; all 7 release-gate tests pass.
  - Suggested owner: whoever owns the DeepEval opt-in lane — broaden the skip-guard to catch the wrapped rate-limit exception shape (or gate the test behind `--run-eval`/a live-quota flag) so a free-tier 429 never reds the default suite.
