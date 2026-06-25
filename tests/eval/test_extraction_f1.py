"""
Eval test stub — per-field-type extraction F1 (D3-07): numeric tolerance match,
boolean exact match, set-overlap F1, refusals scored (not dropped, D3-03), and
the per-confidence-bucket split (D3-04).

Requirement: EXTRACT-03. Wave 0 stub — Plan 04 implements scripts/eval_extraction.py.
Function names are LOCKED; Plan 04 fills the bodies (tiny_extraction_labels
fixture in tests/eval/conftest.py is the input). These are offline scorer-logic
tests (no live services), so they skip on the implementing plan, not on --run-eval.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Plan 04 implements scripts/eval_extraction.py")


def test_numeric_tolerance_match() -> None:
    """A numeric field within F1_NUMERIC_TOLERANCES[field] counts as a match."""
    raise NotImplementedError


def test_boolean_exact_match() -> None:
    """The boolean field (going_concern) matches only on exact equality."""
    raise NotImplementedError


def test_set_overlap_f1() -> None:
    """Set/list fields score by rapidfuzz set-overlap precision/recall F1."""
    raise NotImplementedError


def test_refusal_scored_not_dropped() -> None:
    """A refusal where gold says absent scores as correct, not dropped (D3-03)."""
    raise NotImplementedError


def test_bucket_split() -> None:
    """F1 is reported separately per confidence bucket (high/med/low, D3-04)."""
    raise NotImplementedError
