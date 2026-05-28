"""
Stub: agent/nodes/cite_check.py — deterministic non-LLM cite-check (TRUST-04).

Validates Pattern 3 (01-RESEARCH.md): the cite_check function must:
- Return (False, reasons) when a claim's text does NOT appear at span_offsets in chunk_text
- Reject when token_set_ratio < 80 (paraphrase too distant)
- Reject when a numeric token in the claim is absent from the chunk window (number-set check)
- Return (True, []) only when ALL claims pass both checks

Wave 3 owns this implementation (RAG-02, TRUST-04; T-1-02 mitigation).
"""
from __future__ import annotations

import pytest

pytest.importorskip("agent.nodes.cite_check", reason="agent/nodes/cite_check.py ships in Wave 3")


@pytest.mark.xfail(reason="Wave 3 owns this — implements agent/nodes/cite_check.py", strict=False)
def test_unsupported_claim_rejected() -> None:
    """cite_check() must return (False, [...]) when a claim's text is not supported
    by the cited chunk_text at span_offsets (token_set_ratio < 80 or number mismatch)."""
    assert False, "Wave 3 must implement: construct unsupported Claim, assert cite_check returns False"
