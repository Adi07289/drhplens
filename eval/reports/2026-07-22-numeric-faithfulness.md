# Numeric-Faithfulness Track — 2026-07-22

## Summary

| Metric | Value | Gate | Status |
|---|---|---|---|
| numeric_faithfulness | 0.000 | >= 0.95 (EVAL-03 / D3-12) | FAIL |
| Questions grounded | 0/4 | — | — |

**Interpretation (P10):** numeric_faithfulness is the fraction of numeric-only eval questions whose *every* emitted number grounds to a cited DRHP span via the deterministic, non-LLM cite_check per-number antibody (lakh/crore/million reconciliation + relative tolerance, D3-10). A single hallucinated or mis-reconciled number fails that question. The >= 0.95 release gate (scripts/release_gate.py) physically refuses deploy below this threshold — enforcement, not a printed warning.

## Per-Question Results

| qid | numbers_grounded | status |
|---|---|---|
| num-001 | no | ok |
| num-002 | no | ok |
| num-003 | no | ok |
| num-004 | no | ok |

## Notes

- Numeric eval set: `eval/gold/numeric_eval.jsonl` (Swiggy-anchored; right-sized to the ingested DRHP set per D3-05).
- Grounding reuses `agent.nodes.cite_check.cite_check` — the same deterministic antibody the agent uses at emit time (no LLM judge).
- Generated: 2026-07-22 by scripts/run_eval.py (compute_numeric_faithfulness).