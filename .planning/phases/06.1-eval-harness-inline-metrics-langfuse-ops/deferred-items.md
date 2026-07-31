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
  - **✅ RESOLVED (2026-07-29):** the opt-in lane is now gated on an explicit `RUN_FAITHFULNESS_JUDGE` flag (not mere key-presence — DeepEval auto-loads `.env`), plus `run_async=False` + a skip-on-quota guard. Default `pytest` skips it deterministically regardless of quota. Commit `fdd8bdd` + the flag fix.

## From /gsd-eval-review (2026-07-29, score 64/100 NEEDS WORK — see 06.1-EVAL-REVIEW.md)

Two audit gaps were FIXED (production tracing → `invoke_with_tracing`; citation saturation caveat) + a regression-guard test added. Three gaps remain OPEN — all disclosed, deploy-blocking a PRODUCTION-READY stamp:

- **Faithfulness unmeasured + judge uncalibrated (CRITICAL).** `eval_summary.json` faithfulness = `-1`; the ≥0.7 judge-vs-human calibration on a ≥50-example spot-check is not done. **Blocked:** free-tier `gemini-3.5-flash` is 20 requests/day, so a ≥50-example judge run needs multiple days + human labels — not completable in one session. Do this before surfacing any real (non `-1`) faithfulness number.
- **≥50-example human spot-check (P10) not done** while deterministic figures surface inline. Pairs with the calibration above.
- **No automated CI gate lane.** The deterministic gate is a manual `make release`; only `nightly-nse.yml` exists in GitHub Actions. Add a CI workflow that regenerates the eval artifact + runs `release_gate.py` (fits OPS-02 deploy / a later slice).
- **Gold-set tightening (from spike 003).** Until `expected_sources` are ≤2-3-page spans (+ RPT/numeric coverage), recall AND citation are saturated floors, not discriminating signals.

## From /gsd-code-review (2026-07-29, 0 Critical / 6 Warning / 8 Info — see 06.1-REVIEW.md)

Honesty invariant PASSED. **WR-01 (legacy run_eval crash KeyError) + WR-04 (hardcoded judge_model provenance) FIXED** this session. Remaining warnings deferred (tracked):

- **WR-02 (gate-metric hardening) — DEFERRED, needs care.** `eval/metrics/{citation,recall}.py` return a vacuous `1.0` for empty `expected_sources` and use asymmetric page defaults (expected `[0, 9999]` vs chunk `[0, 0]`), so a *mislabeled* gold entry missing page bounds would match any chunk and silently inflate the HARD-GATED citation metric. Current gold data all has bounds, so measured values are unaffected — but harden it (treat a bound-less expected source as a non-match, not match-all) WITH updated `tests/unit/test_eval_metrics.py` before the gold set grows. Changes shared gate semantics → do deliberately, not in a review pass.
- **WR-03 (requirements.txt ↔ pyproject drift) — DEFERRED to deploy (OPS-02).** `requirements.txt` omits `deepeval`, `google-genai`, `fastembed`, and Phase 4/5 runtime deps; an HF-Spaces install straight from `requirements.txt` would break. Pre-existing debt (not introduced by 6.1). Reconcile the two dep files (and decide ragas → optional-extras) as part of the deploy phase.
- **WR-05 (unguarded json.loads on /methodology) — DEFERRED.** `pages/01_methodology.py:183,213` load `panel_sanity.json`/`card_data.json` without the `.is_file()`+try/except guard the eval read uses; a corrupt file crashes the page. Pre-existing; mirror the eval-read guard.
- Info items (dead code `_STAGES_UNUSED`, stale `policies.py` threshold docstrings, orphan `judge_flag`, unused import, href-scheme note) — low priority, batch later.

## Gold-set tightening — ATTEMPTED 2026-07-30, cannot auto-complete honestly

Tried to derive tight (<=2-3pp) `expected_sources` for the 11 grounded Swiggy Qs by matching
each entry's `expected_answer_contains` substrings against the 1,885 indexed DRHP chunks.
**It does not work reliably** and must NOT be auto-committed (fabricated precision violates the
honesty invariant):
- Distinctive answer NUMBERS are not verbatim in the chunk text: `11,327` (issue size),
  `4,499` (OFS/fresh), `11,247` (revenue) -> **0 chunks** each (Indian number formatting /
  table-extraction differences). `2,350` (net loss) -> **page 431**, but its gold label says
  `[200-300]` — so an existing label is itself questionable.
- Generic substrings over-match: `1` (face value) -> 1,674 chunks; `BSE`/`NSE` -> 80; `related
  party` -> 28 -> meaningless auto-pages (0, 1, 24).
- Only 2-3 entries got a confident content match (swiggy-009 path-to-profitability -> p32,
  swiggy-010 competition/Zomato -> p42).
**Requires a HUMAN reading the Swiggy DRHP PDF** to confirm the real answer page per question
(and to fix formatting so answer numbers are findable). Do NOT ship auto-derived spans. Until
tightened, recall AND citation remain honest saturated floors (already disclosed on the surface
+ report). Bonus finding: the extraction/formatting gap (numbers not verbatim in text) is worth
a look for retrieval quality generally.
