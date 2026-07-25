# Numeric-Faithfulness Release Gate — 2026-07-22

## Decision

| Metric | Value | Gate (>=) | Status |
|---|---|---|---|
| numeric_faithfulness | 0.080 | 0.95 | FAIL |

**Deploy BLOCKED — gate exits non-zero; the build halts here.**

**Interpretation (P10):** numeric_faithfulness is the fraction of numeric-only eval questions (`eval/gold/numeric_eval.jsonl`) whose *every* emitted number grounds to a cited DRHP span via the deterministic, non-LLM cite_check antibody (D3-10). The >= 0.95 threshold is the ROADMAP cross-phase invariant; it is enforced, not relaxed. A FAIL means at least one emitted number could not be grounded — fix the extractor / tune tolerances per the rubric and re-run; do NOT lower the gate.

- Threshold source: `agent.policies.NUMERIC_FAITHFULNESS_GATE`.
- Generated: 2026-07-22 by scripts/release_gate.py.