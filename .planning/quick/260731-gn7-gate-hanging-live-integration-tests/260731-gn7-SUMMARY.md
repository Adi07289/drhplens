---
quick_id: 260731-gn7
slug: gate-hanging-live-integration-tests
description: Gate the hanging live integration tests behind explicit CLI flags
date: 2026-07-31
branch: phase6/6a-eval-harness
status: complete
---

# Quick Task 260731-gn7 — Summary

## Outcome
Isolated and eliminated the pre-`/gsd-ship` pytest wedge. A bare `pytest` under `.env`
(the dev / `/gsd-ship` / CI condition) no longer runs any live service and no longer hangs.

## Root cause (isolated this session)
Live tests were gated on **env-var presence**, but the **deepeval pytest plugin and the
langfuse SDK auto-load `.env` at session start**, so those gates never fired on any box
with a `.env` file. Confirmed empirically: stripping `QDRANT_URL`/`GEMINI_API_KEY` from the
shell did **not** stop the tests — `test_agent_e2e.py` still ran live for **72.17 s**.

Two offenders, both gated only by env presence:
- **`tests/integration/test_agent_e2e.py`** — 5 tests → live Qdrant + Gemini graph invokes.
  72 s with 3/5 running; `test_gold_set_smoke_subset` = 3 sequential live invokes → full
  gold set > 2 min. pytest-timeout is `method=signal` (per-test) and tenacity retries stall
  past it.
- **`tests/integration/test_langfuse_trace.py`** — `test_langfuse_client_initialized_when_
  keys_present` + `test_every_node_writes_a_span_with_claim_ids` construct a real client →
  **~15 s `atexit` flush** to `cloud.langfuse.com` at teardown (uncovered by the per-test
  signal timeout; observed wall 17.46 s vs 2.24 s test time).

## Changes
1. **`tests/integration/test_agent_e2e.py`** — added `autouse` module fixture
   `_require_run_eval_flag(request)` that skips unless `--run-eval`. Kept the existing
   `_MISSING`/`xfail(run=False)` block as a secondary guard.
2. **`tests/integration/test_langfuse_trace.py`** — added a `--run-langfuse` `pytest.skip`
   guard to the two live-client tests (mirroring the existing `test_emit_enriched_trace_
   live_attach`); kept `@_langfuse_skip` for defense in depth. Mocked / `classify_*` tests
   untouched.

Both flags (`--run-eval`, `--run-langfuse`) already existed in `tests/conftest.py`. Explicit
CLI flags are the only gate `.env` auto-load cannot defeat — same pattern as `NSE_LIVE_SMOKE`.

## Verification (quota-free — the live agent was NOT run)
- Two files under `.env`, **no flags**: all 5 e2e + both live-langfuse tests SKIP; test time
  **0.46 s**; the ~15 s teardown flush is **gone** (no client constructed).
- Two files `--collect-only --run-eval --run-langfuse`: flags recognized, tests activate.
- Whole suite `--collect-only`: **624 tests, 0 collection errors**.
- **Full suite under `.env`, no flags: 605 passed, 17 skipped, 2 xfailed in 74 s** — no
  wedge (finished well under a 240 s cap), no regressions. Matches the prior 605-pass baseline.

## Notes
- The `.planning/STATE.md` docs commit also carried a **pre-existing** (not-this-task)
  frontmatter state transition (`executing`→`verifying`, phase/plan counts) left uncommitted
  from a prior 2026-07-30 session.
- Follow-up (out of scope): per-test `pytest-timeout` doesn't cover teardown/`atexit`. Now
  that live paths are flag-gated it's unnecessary; add a session-level wall-clock guard only
  if a future live path stalls at teardown.
- `/gsd-ship` blocker "ISOLATE THE HANGING LIVE TEST" is resolved.
