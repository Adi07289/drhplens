---
phase: 01-foundation-mvp-a-cited-q-a-on-one-ipo
plan: "06"
subsystem: deploy-observability-eval
tags: [hf-spaces, langfuse, eval, gold-set, gate1-calibration, phase1-close]
dependency_graph:
  requires: [01-04, 01-05]
  provides: [OPS-02, langfuse-instrumentation, eval-baseline, gate1-calibration-script]
  affects: [Phase-2-skeleton-inheritance, Phase-3-METHOD-01-trace-consumer]
tech_stack:
  added: [langfuse, RAGAS]
  patterns: [no-op-fallback, invoke_with_tracing, custom-langfuse-score, calibration-sweep]
key_files:
  created:
    - README.md
    - docs/DEPLOY.md
    - app/observability/__init__.py
    - app/observability/langfuse_client.py
    - app/observability/trace_decorators.py
    - app/observability/cite_check_metric.py
    - scripts/run_eval.py
    - scripts/calibrate_gate1.py
    - scripts/cron_pinger.yml
    - tests/eval/gold_set.jsonl (content; schema locked Wave 0)
    - tests/eval/test_phase1_eval.py (replaced xfail stub)
    - eval/reports/.gitkeep
  modified:
    - agent/graph.py (invoke_with_tracing wrapper)
    - agent/nodes/generate.py (attach_claim_ids_to_span)
    - agent/nodes/cite_check.py (score_cite_check + attach_claim_ids_to_span)
    - agent/nodes/gate1_check.py (attach_gate1_metadata_to_span)
    - agent/nodes/refuse_with_reformulation.py (attach_refusal_reason_to_trace)
    - agent/policies.py (GATE1_THRESHOLD calibration annotation)
    - .env.example (LANGFUSE_HOST= added as explicit key)
    - tests/conftest.py (--run-langfuse + --run-eval CLI options; gold_set fixture wired)
    - tests/integration/test_langfuse_trace.py (xfail stub replaced with full test body)
decisions:
  - "No-op-when-disabled: all observability helpers short-circuit when LANGFUSE_PUBLIC_KEY is unset so local dev requires zero credentials beyond Qdrant+Gemini"
  - "invoke_with_tracing as thin wrapper: existing GRAPH.invoke continues to work for unit tests; tracing is additive not breaking"
  - "score_cite_check uses get_client() (lru_cache singleton) not get_callback_handler() — Langfuse custom scores go through the REST client, not the LangChain callback handler"
  - "GATE1_THRESHOLD stays at 0.0 default until user runs calibrate_gate1.py against the live Qdrant cluster; the annotation in policies.py records the procedure"
  - "gold_set refusal-eligible category (correct Wave 0 schema had 'refusal' not 'refusal-eligible') — used 'refusal-eligible' per plan spec in 01-06-PLAN.md Task 3"
metrics:
  duration: "2026-05-28"
  completed: "2026-05-28"
  tasks_completed: 3
  tasks_user_setup: 3
  unit_tests_passing: 219
  integration_tests_deferred: 4
---

# Phase 1 Plan 06: HF Spaces Deploy + Langfuse Instrumentation + Eval — Summary

Wave 5 ships the deploy config, observability layer, and eval infrastructure for DRHPLens Phase 1. Three autonomous code tasks are complete and committed. Three user_setup tasks (live HF deploy, cold-start verification, Phase 1 formal close) require a human with the live credentials and dashboard access.

## What Was Built (autonomous tasks)

### Task 1 — HF Spaces config + deploy runbook
- `README.md` with HF Spaces YAML frontmatter: `sdk: streamlit`, `sleep_time: 1800` (max free-tier cold-start mitigation per RESEARCH §Pitfall 6), `app_file: app.py`
- `.env.example` updated: `LANGFUSE_HOST=https://cloud.langfuse.com` added as explicit (non-comment) key — all 7 required env vars now documented
- `docs/DEPLOY.md`: 12-step manual deploy runbook covering Langfuse account creation, HF Space creation, secrets configuration, smoke test checklist, cron pinger setup (options A/B), cold-start verify, eval + calibration runs. Includes Qdrant 1GB sizing callout (CEO review T6).

### Task 2 — Langfuse instrumentation
- `app/observability/langfuse_client.py`: `is_enabled()`, `get_client()` (lru_cache), `get_callback_handler()` with `_NoOpCallbackHandler` fallback
- `app/observability/trace_decorators.py`: `build_callbacks_for_run()`, `attach_claim_ids_to_span()`, `attach_refusal_reason_to_trace()`, `attach_gate1_metadata_to_span()` — all four no-op when disabled
- `app/observability/cite_check_metric.py`: `score_cite_check()` — logs `faithfulness_via_cite_check` custom Langfuse score (1.0 = all grounded, 0.0 = any unsupported)
- `agent/graph.py`: `invoke_with_tracing(state, question)` wrapper — existing `GRAPH.invoke()` unchanged for unit tests
- Nodes wired: `generate` → `attach_claim_ids_to_span`; `cite_check` → `score_cite_check + attach_claim_ids_to_span`; `gate1_check` → `attach_gate1_metadata_to_span`; `refuse_with_reformulation` → `attach_refusal_reason_to_trace`
- `tests/integration/test_langfuse_trace.py`: xfail stub replaced; `test_langfuse_client_noop_when_keys_missing` always runs (passes); 4 live tests skip without `--run-langfuse`

### Task 3 — Gold set + eval suite
- `tests/eval/gold_set.jsonl`: 13 entries against Swiggy DRHP (5 factual + 3 numeric + 3 risk-factor + 2 refusal-eligible); TBD-WAVE5 stubs replaced with real questions
- `scripts/run_eval.py`: citation accuracy + answer coverage + RAGAS faithfulness + recall@5; emits `eval/reports/<date>-phase1-baseline.md`
- `scripts/calibrate_gate1.py`: sweeps GATE1_THRESHOLD from -2.0 to +2.0 in 0.5 steps; prints recommended threshold for `agent/policies.py`
- `scripts/cron_pinger.yml`: Option B GitHub Actions workflow (copy to `.github/workflows/ping.yml` to enable)
- `eval/reports/.gitkeep`: directory tracked for first report

## User_Setup Tasks (pending — not executable by Claude Code)

### Task 4 — Public HF Spaces deploy (blocking)
Runbook: `docs/DEPLOY.md` steps 1-9. Requires HF account, Langfuse Cloud account, all 7 env vars configured in Space secrets UI. Cannot be automated (HF Spaces creation and secrets-write are UI-only for free-tier accounts).

### Task 5 — Gate 1 calibration run (manual)
After Task 4 deploys, run locally:
```bash
python scripts/calibrate_gate1.py
```
Update `agent/policies.py:GATE1_THRESHOLD` with the recommended value + inline comment. Push and let the Space rebuild.

### Task 6 — Phase 1 formal close (manual)
After Task 4 + 5 complete:
1. Flip `01-VALIDATION.md` frontmatter: `nyquist_compliant: true`
2. Walk Per-Task Verification Map — update all rows to green
3. Commit `01-06-SUMMARY.md` with the public URL + eval baseline + calibrated threshold

## Phase 1 REQ Traceability

| REQ | Description | Status | Closing artifact |
|---|---|---|---|
| INGEST-01 | Swiggy DRHP PDF committed + SHA-256 pinned | done | `pytest tests/unit/test_drhp_integrity.py` (Wave 0) |
| INGEST-02 | Docling parses > 100 sections | done | `pytest tests/unit/test_parser.py` (Wave 2) |
| INGEST-03 | 1,500-2,500 chunks with valid payload | done | `pytest tests/unit/test_chunker.py` (Wave 2) |
| RAG-01 | End-to-end cited Q&A | done | `python -m agent.demo "What is Swiggy's issue size?"` (Wave 3+4) |
| RAG-02 | Span-level citations | done | `pytest tests/unit/test_citation_renderer.py` (Wave 1+4) |
| RAG-03 | Refusal posture with reformulation | done | `pytest tests/unit/test_refuse_with_reformulation.py` (Wave 3) |
| TRUST-01 | Three disclaimer surfaces | done | `pytest tests/unit/test_disclaimer_surface.py` (Wave 1+4) |
| TRUST-02 | Banned-token scrubber | done | `pytest tests/unit/test_scrubber.py` (Wave 1+3) |
| TRUST-03 | SEBI RA compliance posture | done (legal gate Phase 6) | `pytest tests/unit/test_copy_no_banned_tokens.py` |
| TRUST-04 | Non-LLM deterministic cite-check | done | `pytest tests/unit/test_cite_check.py` (Wave 1+3) |
| UI-01 | Mobile-responsive (375px) | done | Wave 4 Streamlit + live smoke test (user_setup T4) |
| UI-02 | Citation chips expand to source | done | `pytest tests/unit/test_citation_renderer.py` (Wave 4) |
| OPS-02 | Publicly deployed on free-tier host | code-complete; awaiting user_setup T4 | `README.md` YAML frontmatter + `docs/DEPLOY.md` |

## Test Counts

| Suite | Count | Status |
|---|---|---|
| Unit tests (`tests/unit/`) | 219 | passing (sentence-transformers pre-existing skip excluded) |
| Integration — no-op Langfuse | 1 | passing always |
| Integration — live Langfuse | 4 | deferred (--run-langfuse gate) |
| Eval suite | 1 | deferred (--run-eval gate; requires live env vars) |

## Deviations from Plan

**1. [Rule 2 - Missing key] gold_set.jsonl: category "refusal" → "refusal-eligible"**
- Wave 0 schema had `"refusal"` as the category value in 2 entries; plan Task 3 spec uses `"refusal-eligible"` throughout.
- Used `"refusal-eligible"` per the Task 3 spec, ensuring consistency with distribution table (5+3+3+2).

**2. [Rule 2 - Missing key] .env.example: LANGFUSE_HOST commented out → explicit**
- Wave 0 committed `# LANGFUSE_HOST=https://cloud.langfuse.com` as a comment. Plan requires it as an explicit fillable key.
- Changed to `LANGFUSE_HOST=https://cloud.langfuse.com` (uncommented, with default value) so HF Spaces secrets-add step is clear.

**3. [Rule 3 - Scope note] pages/01_methodology.py FLAG-GITHUB-URL**
- Plan Task 1 mentions replacing `FLAG-GITHUB-URL` placeholder in `pages/01_methodology.py`. That file was not listed as modified in the plan's `files_modified` and is owned by Wave 4. No change made to avoid scope creep; documented here for user find-and-replace before ship.

## Known Stubs

| File | Line | Stub | Reason |
|---|---|---|---|
| `agent/policies.py` | GATE1_THRESHOLD | `0.0` (pre-calibration default) | Calibrated value requires running `scripts/calibrate_gate1.py` against live Qdrant (user_setup T5) |
| `scripts/cron_pinger.yml` | URL line | `<user>` placeholder | User must replace with HF username before enabling Option B |

## Threat Flags

No new threat surface introduced beyond what is in the plan's `<threat_model>`. All 5 boundaries (T-1-03, T-1-04, T-1-05, T-1-06, T-1-08, T-1-09) are addressed as designed.

## Cross-Cutting Claim_ID Trace Invariant

`invoke_with_tracing()` is the new preferred call site for app.py and agent.demo. When `LANGFUSE_PUBLIC_KEY` is set, every agent run produces a trace with:
- `intake`, `retrieve`, `rerank`, `gate1_check`, `decompose`, `generate`, `scrub`, `cite_check`, `emit` spans (9-span shape per RESEARCH)
- `claim_ids` list on `generate` and `cite_check` spans (Phase 3 METHOD-01 consumer contract)
- `faithfulness_via_cite_check` custom score (1.0 or 0.0) on grounded-answer traces
- `refusal_reason ∈ {low_retrieval_score, unsupported_claim, banned_token, infrastructure_error}` on refusal traces
- `gate1_max_score`, `gate1_threshold`, `gate1_passed` on gate1_check spans (calibration data)

## Self-Check: PASSED

Files exist:
- README.md ✓
- docs/DEPLOY.md ✓
- app/observability/{__init__,langfuse_client,trace_decorators,cite_check_metric}.py ✓
- scripts/{run_eval,calibrate_gate1,cron_pinger.yml} ✓
- tests/eval/gold_set.jsonl (13 entries, correct distribution) ✓
- eval/reports/.gitkeep ✓

Commits:
- 1d3df4b feat(01-06): HF Spaces config + deploy runbook (Task 1) ✓
- ea18b5d feat(01-06): Langfuse instrumentation + invoke_with_tracing (Task 2) ✓
- 8c85db9 feat(01-06): eval suite + gold set + Gate 1 calibration script (Task 3) ✓

Unit tests: 219 passing ✓
