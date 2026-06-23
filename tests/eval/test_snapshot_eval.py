"""
Eval test stub — financials snapshot cited spans actually support the summary
(faithfulness >= Phase 1 baseline) (no threat — measurement, not security).

Requirement: SNAP-04. Threat: none.
Secure behavior: the key-financials snapshot block's cited spans actually
support the prose summary (faithfulness check), measured against the
extended gold set.

Wave 0 stub — Wave 5 implements (02-VALIDATION.md row "2-snapshot-faithfulness").
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
def test_snapshot_financials_faithfulness() -> None:
    raise NotImplementedError
