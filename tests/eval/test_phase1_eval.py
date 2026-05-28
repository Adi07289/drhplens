"""
Stub: eval test — Phase 1 gold-set evaluation (RAG-01, RAG-02, RAG-03, TRUST-04).

Validates the full gold-set baseline:
- 10-15 hand-curated Q/A/source-span entries from tests/eval/gold_set.jsonl
- Faithfulness, context recall@k, citation accuracy metrics computed via RAGAS
- Numeric faithfulness: every numeric value in expected_answer_contains appears in the answer

Wave 5 owns this implementation (requires --run-eval flag; calls Gemini API).
"""
from __future__ import annotations

import pytest

pytest.importorskip("ragas", reason="ragas and full gold set ship in Wave 5")


@pytest.mark.xfail(reason="Wave 5 owns this — populates gold_set.jsonl and runs RAGAS evals", strict=False)
@pytest.mark.eval
def test_gold_set_numeric_faithfulness_baseline(gold_set) -> None:
    """All gold-set numeric questions must produce answers where every expected number
    appears verbatim. Baseline measurement establishes the Phase 3 release threshold."""
    assert False, "Wave 5 must implement: run agent on gold_set, compute numeric faithfulness, record baseline"
