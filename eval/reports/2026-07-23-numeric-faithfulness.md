# Numeric-Faithfulness Track — 2026-07-23

## Summary

| Metric | Value | Gate | Status |
|---|---|---|---|
| numeric_faithfulness | 0.000 | >= 0.95 (EVAL-03 / D3-12) | FAIL |
| Questions grounded | 0/50 | — | — |

**Interpretation (P10):** numeric_faithfulness is the fraction of numeric-only eval questions whose *every* emitted number grounds to a cited DRHP span via the deterministic, non-LLM cite_check per-number antibody (lakh/crore/million reconciliation + relative tolerance, D3-10). A single hallucinated or mis-reconciled number fails that question. The >= 0.95 release gate (scripts/release_gate.py) physically refuses deploy below this threshold — enforcement, not a printed warning.

## Per-Question Results

| qid | numbers_grounded | status |
|---|---|---|
| num-001 | no | ok |
| num-002 | no | ok |
| num-003 | no | ok |
| num-004 | no | ok |
| num-005 | no | ok |
| num-006 | no | ok |
| num-007 | no | crashed |
| num-008 | no | crashed |
| num-009 | no | crashed |
| num-010 | no | crashed |
| num-011 | no | crashed |
| num-012 | no | crashed |
| num-013 | no | crashed |
| num-014 | no | crashed |
| num-015 | no | crashed |
| num-016 | no | crashed |
| num-017 | no | crashed |
| num-018 | no | crashed |
| num-019 | no | crashed |
| num-020 | no | crashed |
| num-021 | no | crashed |
| num-022 | no | crashed |
| num-023 | no | crashed |
| num-024 | no | crashed |
| num-025 | no | crashed |
| num-026 | no | crashed |
| num-027 | no | crashed |
| num-028 | no | crashed |
| num-029 | no | crashed |
| num-030 | no | crashed |
| num-031 | no | crashed |
| num-032 | no | crashed |
| num-033 | no | crashed |
| num-034 | no | crashed |
| num-035 | no | crashed |
| num-036 | no | crashed |
| num-037 | no | crashed |
| num-038 | no | crashed |
| num-039 | no | crashed |
| num-040 | no | crashed |
| num-041 | no | crashed |
| num-042 | no | crashed |
| num-043 | no | crashed |
| num-044 | no | crashed |
| num-045 | no | crashed |
| num-046 | no | crashed |
| num-047 | no | crashed |
| num-048 | no | crashed |
| num-049 | no | crashed |
| num-050 | no | crashed |

## Notes

- Numeric eval set: `eval/gold/numeric_eval.jsonl` (Swiggy-anchored; right-sized to the ingested DRHP set per D3-05).
- Grounding reuses `agent.nodes.cite_check.cite_check` — the same deterministic antibody the agent uses at emit time (no LLM judge).
- Generated: 2026-07-23 by scripts/run_eval.py (compute_numeric_faithfulness).