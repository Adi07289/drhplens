---
phase: 03-structured-signal-extraction-red-flag-table
plan: 05
subsystem: eval + deploy-tooling
tags: [numeric-faithfulness, release-gate, enforcement, eval-harness, offline-ci, checkpoint-pending]

# Dependency graph
requires:
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 01
    provides: NUMERIC_FAITHFULNESS_GATE policy constant, Wave 0 test_release_gate stub
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 02
    provides: extended cite_check per-number grounding (lakh/crore reconciliation + tolerance) reused by the numeric track
provides:
  - "eval/gold/numeric_eval.jsonl — 50 Swiggy-anchored numeric-only Qs with arithmetically-correct gold_numeric + gold_unit + source_page (D3-11)"
  - "scripts/run_eval.py::compute_numeric_faithfulness — importable numeric-faithfulness computation reusing cite_check grounding; dated numeric-track report (D3-11/D3-13)"
  - "scripts/release_gate.py::enforce_gate — pure, live-infra-free gate: sys.exit(1)+report below NUMERIC_FAITHFULNESS_GATE, pass at/above (D3-12)"
  - "Makefile release target — invokes the gate; Make halts on non-zero exit (enforcement)"
affects: [03-06 UI/methodology-pane reads the numeric-track report; deploy runbook gates on make release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-layer gate: pure enforce_gate(score) (offline-unit-testable, no live import) + main() that owns the single live call — testability + enforcement in one module"
    - "Numeric track reuses the agent's own cite_check antibody (same deterministic per-number grounding at eval time as at emit time) — no LLM judge, no duplicated numeric logic"
    - "Threshold from agent.policies (no literal 0.95 in the gate decision), mirroring the single-source-of-truth policies posture"

key-files:
  created:
    - eval/gold/numeric_eval.jsonl
    - scripts/release_gate.py
    - Makefile
  modified:
    - scripts/run_eval.py
    - tests/eval/test_release_gate.py

key-decisions:
  - "Gold set is right-sized to the ONLY ingested DRHP (swiggy_2024_11) per D3-05 — 50 Swiggy-anchored numeric Qs with honest n; 20-30 multi-IPO remains the documented target bounded by live ingest (data/INGEST_ALL_LATER.md)"
  - "Every gold_numeric is arithmetically correct and traceable: lakh/crore conversions use 1 crore = 100 lakh (11,327.43 cr = 11,32,743 lakh), explicitly NOT the off-by-10x 1,12,470-lakh figure in 03-RESEARCH/03-PATTERNS"
  - "enforce_gate takes the score directly so the offline fixture test needs no monkeypatch of a live call; the live compute_numeric_faithfulness lives only in main()"
  - "Gold OFS/fresh split uses the REAL Swiggy figures (fresh 4,499 cr / OFS 6,828.43 cr, 39.72%/60.28%), not the snapshot's hand-authored 59/41 placeholder — gold answers must trace to real source figures, not to a CODE-NOW seed"

requirements-completed: []  # EVAL-03 completes only after the live make-release checkpoint (Task 3) is verified

# Metrics
duration: ~25min
completed: 2026-06-25
---

# Phase 3 Plan 05: Numeric-Faithfulness Release Gate Summary

**A 50-question Swiggy-anchored numeric eval set (every gold answer arithmetically correct), an importable `compute_numeric_faithfulness` track that reuses the Plan 02 cite_check per-number antibody, and a two-layer `make release` gate whose pure `enforce_gate` physically refuses deploy (sys.exit(1) + dated report) below the policy threshold and is unit-tested offline at 0.94/0.95/0.96 — with the LIVE gate run left as a blocking human-verify checkpoint (no live services in this environment).**

## Status: AUTONOMOUS WORK COMPLETE — Task 3 (live `make release`) PENDING at checkpoint

Tasks 1 and 2 (all offline-buildable work) are code-complete, committed, and green. Task 3 is the `checkpoint:human-verify` live run; it requires `GEMINI_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` and ingested DRHPs, none of which are available in this execution environment. Per the plan's `autonomous: false` posture it is intentionally left pending for human verification.

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 of 3 autonomous tasks complete (Task 3 is a human-verify checkpoint, not run)
- **Files:** 3 created, 2 modified

## Accomplishments

- **Task 1 (D3-11/D3-13):** `eval/gold/numeric_eval.jsonl` — 50 numeric-only questions, all anchored to the single ingested DRHP (`swiggy_2024_11`, per D3-05). Each row carries `qid`, `question`, `gold_numeric`, `gold_unit`, `source_page`, plus `expected_answer_contains`/`expected_sources` for the harness. Coverage spans issue-size / fresh / OFS / price-band / allocation / multi-year financials / derived ratios and growth, and includes the Swiggy lakh/crore anchors (revenue 11,247 cr; fresh 4,499 cr) so the Plan 02 reconciliation is exercised. Extended `scripts/run_eval.py` additively with `compute_numeric_faithfulness` (reuses `agent.nodes.cite_check.cite_check` per-number grounding; returns the aggregate score for the gate; writes a dated numeric-track report). The Phase 1 track is untouched.
- **Task 2 (D3-12):** `scripts/release_gate.py` with a pure `enforce_gate(numeric_faithfulness, report_dir=...)` that reads `agent.policies.NUMERIC_FAITHFULNESS_GATE`, writes a dated `*-numeric-gate.md` report, and `sys.exit(1)` below threshold / passes at-or-above (>= boundary). `main()` owns the only live call (via `compute_numeric_faithfulness`). `Makefile` `release:` target invokes the gate so Make halts on non-zero exit. `tests/eval/test_release_gate.py` flipped skip→green: 0.94 → non-zero exit + report written; 0.95 and 0.96 → pass.

## Task Commits

1. **Task 1** (numeric eval set + run_eval track) — `1c6f927` (feat)
2. **Task 2 RED** (failing offline gate-logic test) — `561b06e` (test)
3. **Task 2 GREEN** (release_gate.py + Makefile) — `d5db2a4` (feat)

## Decisions Made

- **Honest, right-sized gold set (D3-05):** only `swiggy_2024_11` is ingested, so all 50 Qs are Swiggy-anchored with honest n; the 20-30 multi-IPO target stays documented, bounded by live ingest. No fabricated figures for non-ingested IPOs.
- **Arithmetic correctness is a hard requirement:** every `gold_numeric` is self-consistent and traceable. Lakh/crore conversions use 1 crore = 100 lakh (11,327.43 cr = 11,32,743 lakh; 11,247.39 cr = 11,24,739 lakh). The off-by-10x "1,12,470 lakh" figure in 03-RESEARCH §Pattern 6 / 03-PATTERNS was deliberately NOT copied (it is the same error 03-02-SUMMARY flagged).
- **Real source figures over the placeholder seed:** the fresh/OFS split uses the real Swiggy numbers (fresh 4,499 cr / OFS 6,828.43 cr; 39.72% / 60.28%), not the snapshot's hand-authored 59/41 CODE-NOW placeholder, because gold answers must trace to actual source figures.
- **Two-layer gate for testability + enforcement:** `enforce_gate` takes the score directly (no live import, no monkeypatch needed offline); the live computation lives only in `main()`.

## Deviations from Plan

### Auto-fixed Issues

None of substance. The gold set is independent of the snapshot seed by design (see Decisions); using the real Swiggy fresh/OFS figures rather than the placeholder 59/41 split is a data-correctness choice the plan explicitly required ("arithmetically correct and traceable to a real source figure"), not a deviation from the plan's `<action>`. Two docstring rewordings in `release_gate.py` (removing literal `0.95` and the `Qdrant`/`Gemini` tokens from the `enforce_gate` region) were made to satisfy the plan's own acceptance greps; behavior unchanged.

**Total deviations:** 0 functional. Production logic matches the plan's `<action>`/`<behavior>` directives.

## TDD Gate Compliance

Task 2 followed RED → GREEN:
- RED: `561b06e` (test) — confirmed failing on `ModuleNotFoundError: scripts.release_gate`.
- GREEN: `d5db2a4` (feat) — both fixture tests pass.
No `feat` shipped behavior without a corresponding green test. No REFACTOR commit needed (clean on first GREEN). Task 1 is a data-asset + additive-harness task (not behavior-adding TDD); committed as a single `feat`.

## Verification

- `.venv/bin/python -m pytest tests/eval/test_release_gate.py -q` — 2 passed (flipped from skip).
- `.venv/bin/python -m pytest -q` whole suite — **292 passed, 1 failed, 14 skipped, 7 xfailed**. The single failure is the pre-existing, out-of-scope `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` (missing `sentence-transformers`), documented ignorable in STATE.md. No regression.
- Numeric-eval import assertion: 50 rows, all with `gold_numeric` + `source_page`; arithmetic self-consistency (total = fresh + OFS; lakh = crore × 100; pct sum = 100; derived growth/margin checks) all pass.
- Acceptance greps: threshold-from-policy present (`NUMERIC_FAITHFULNESS_GATE` in gate, count ≥ 1); no literal `0.95` in the gate body (count 0); `enforce_gate` region has no `qdrant|genai` import (live call only in `main`); `Makefile` has `release:` invoking `release_gate`.
- `grep -v '^#' scripts/run_eval.py | grep -Ec 'cite_check'` = 8 (numeric track reuses cite_check grounding).

## Known Stubs

None. All Task 1/2 code paths are fully wired and exercised by green offline tests. The live `make release` run is a deliberate gated checkpoint (Task 3), not a stub.

## Checkpoint — Task 3 (LIVE `make release`) PENDING

Task 3 is `checkpoint:human-verify` (`gate="blocking"`) and was NOT run — this environment has no `GEMINI_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` and no live-ingested Qdrant. To complete EVAL-03:

1. Ensure `.env` has `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` and `swiggy_2024_11` is ingested into live Qdrant.
2. Run: `make release`
3. Expected: if `numeric_faithfulness >= 0.95`, prints OK and exits 0; if `< 0.95`, EXITS NON-ZERO and writes `eval/reports/<date>-numeric-gate.md` (the gate working as designed).
4. If it fails below 0.95: inspect the report, tune tolerances/eval scope per the rubric — do NOT lower the 0.95 threshold.
5. Commit the resulting `eval/reports/<date>-numeric-gate.md` and reply "approved" with the observed `numeric_faithfulness` + the committed report path.

Only after this checkpoint is verified should EVAL-03 be marked complete and the plan closed.

## Self-Check: PASSED

- `eval/gold/numeric_eval.jsonl`, `scripts/release_gate.py`, `Makefile` present on disk; `scripts/run_eval.py`, `tests/eval/test_release_gate.py` modified.
- Commits `1c6f927`, `561b06e`, `d5db2a4` present in git history.

---
*Phase: 03-structured-signal-extraction-red-flag-table*
*Completed (autonomous tasks): 2026-06-25 — Task 3 live checkpoint pending*
