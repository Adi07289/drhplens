"""
Eval test stub — Indian-finance recall probe (lakh/crore/RPT/QIB queries) —
gates the hybrid-retrieval decision (Pitfall P13) (no threat — measurement).

Requirement: (P13). Threat: none.
Secure behavior: a 10-query Indian-finance recall@10 probe is run across 2-3
IPOs; the measured recall number gates whether the hybrid-retrieval (BM25 +
dense) wave is scheduled or skipped.

Wave 0 stub — Wave 5 implements (02-VALIDATION.md row "2-p13-recall-probe").
Gated the same way Phase 1 gates tests/eval/test_phase1_eval.py: skip unless
--run-eval (or RUN_EVAL env var) is present (deferred).
"""
from __future__ import annotations

import os
import sys

import pytest

_RUN_EVAL = os.environ.get("RUN_EVAL") or any("--run-eval" in arg for arg in sys.argv)

pytestmark = pytest.mark.skipif(
    not _RUN_EVAL,
    reason="eval suite requires --run-eval flag and live env vars (GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY)",
)


@pytest.mark.eval
@pytest.mark.xfail(reason="Wave 5 — not yet implemented", strict=False)
def test_indian_finance_recall_probe() -> None:
    raise NotImplementedError
