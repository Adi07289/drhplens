"""
Unit test stub — per-number source-grounding (D3-10): lakh/crore reconciliation,
rupee-symbol tolerance, and blocking of an ungrounded number. Extends the
non-LLM cite_check numeric antibody.

Requirement: EVAL-03. Wave 0 stub — Plan 02 extends agent/nodes/cite_check.py
(_numbers_subset gains unit normalization + NUMERIC_GROUNDING_REL_TOLERANCE).
Function names are LOCKED; Plan 02 fills the bodies.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Plan 02 extends agent/nodes/cite_check.py for per-number grounding"
)


def test_lakh_crore_reconciles() -> None:
    """'₹11,247 crore' grounds against '1,12,470 lakh' after unit normalization."""
    raise NotImplementedError


def test_rupee_symbol_tolerance() -> None:
    """A rupee-symbol/format variant of the same number still grounds."""
    raise NotImplementedError


def test_ungrounded_number_blocked() -> None:
    """A number with no matching cited-span source fails the grounding check."""
    raise NotImplementedError
