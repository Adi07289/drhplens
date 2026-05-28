"""
Eval test — Phase 1 gold-set evaluation baseline.

Gated by --run-eval CLI flag (requires live Qdrant + Gemini + all env vars).
Invokes scripts/run_eval.py main logic and asserts the report is produced.

Phase 1 MEASURES but does NOT release-gate:
  - Citation accuracy release gate: Phase 3 EVAL-03
  - RAGAS faithfulness release gate: Phase 6 EVAL-01

Usage:
    pytest tests/eval/test_phase1_eval.py --run-eval
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Gate: skip unless --run-eval is passed
# ---------------------------------------------------------------------------

_RUN_EVAL = os.environ.get("RUN_EVAL") or any("--run-eval" in arg for arg in sys.argv)

pytestmark = pytest.mark.skipif(
    not _RUN_EVAL,
    reason="eval suite requires --run-eval flag and live env vars (GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY)",
)


@pytest.mark.eval
def test_phase1_eval_baseline(tmp_path) -> None:
    """Run the full eval suite and assert the markdown report is produced.

    Phase 1 baseline measurement: records citation accuracy, RAGAS faithfulness,
    recall@5, and refusal correctness against the 13-entry gold set.
    No metric thresholds are enforced at Phase 1 — this is a measurement run.
    """
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    from scripts.run_eval import run_eval

    report_path = run_eval(
        gold_set_path="tests/eval/gold_set.jsonl",
        output_dir=str(tmp_path),
    )

    assert report_path.exists(), f"Eval report not written: {report_path}"
    content = report_path.read_text(encoding="utf-8")
    assert "## Summary" in content, "Report missing Summary section"
    assert "## Per-Entry Results" in content, "Report missing Per-Entry Results section"
    assert "## Gold Set Statistics" in content, "Report missing Gold Set Statistics section"
    assert "swiggy-001" in content or "factual" in content, "Report missing gold set data"
    print(f"\nEval report: {report_path}")
    print(f"Report size: {len(content)} chars")
