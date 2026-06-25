"""
Eval tests — per-field-type extraction F1 (D3-07): numeric tolerance match,
boolean exact match, set-overlap F1, refusals scored (not dropped, D3-03), and
the per-confidence-bucket split (D3-04).

Requirement: EXTRACT-03. Plan 04 implements scripts/eval_extraction.py; these
tests (locked names) exercise the scorer LOGIC offline — no live Qdrant/Gemini,
no cached data/redflag/*.json required. Inputs come from the tiny_extraction_labels
fixture (tests/eval/conftest.py).
"""
from __future__ import annotations

from scripts.eval_extraction import (
    boolean_match,
    bucket_split,
    numeric_match,
    refusal_matches_absence,
    score_field,
    set_overlap_f1,
)


def test_numeric_tolerance_match() -> None:
    """A numeric field within F1_NUMERIC_TOLERANCES[field] counts as a match."""
    from agent.policies import F1_NUMERIC_TOLERANCES

    tol = F1_NUMERIC_TOLERANCES["rpt_pct"]
    # Within tolerance -> match.
    assert numeric_match(3.4 + tol, 3.4, tol) is True
    assert numeric_match(3.4 - tol, 3.4, tol) is True
    assert numeric_match(3.4, 3.4, tol) is True
    # Outside tolerance -> miss.
    assert numeric_match(3.4 + tol + 0.01, 3.4, tol) is False
    assert numeric_match(10.0, 3.4, tol) is False
    # score_field dispatches numeric on the gold row's field_type.
    row = {
        "field_key": "rpt_pct",
        "field_type": "numeric",
        "gold_value": 3.4,
    }
    assert score_field(row, 3.4 + tol / 2) == 1.0
    assert score_field(row, 99.0) == 0.0


def test_boolean_exact_match() -> None:
    """The boolean field (going_concern) matches only on exact equality."""
    assert boolean_match(False, False) is True
    assert boolean_match(True, True) is True
    assert boolean_match(True, False) is False
    assert boolean_match(False, True) is False
    row = {
        "field_key": "going_concern",
        "field_type": "boolean",
        "gold_value": False,
    }
    assert score_field(row, False) == 1.0
    assert score_field(row, True) == 0.0


def test_set_overlap_f1() -> None:
    """Set/list fields score by rapidfuzz set-overlap precision/recall F1."""
    # Empty/empty -> correctly-empty agreement.
    assert set_overlap_f1([], []) == 1.0
    # Fully overlapping -> 1.0.
    assert set_overlap_f1(["Customer A", "Customer B"], ["Customer A", "Customer B"]) == 1.0
    # Disjoint -> 0.0.
    assert set_overlap_f1(["X Corp"], ["Customer A"]) == 0.0
    # Fuzzy near-match still counts (token_set_ratio >= thresh).
    f1_fuzzy = set_overlap_f1(["S.R. Batliboi & Associates LLP"], ["S.R. Batliboi and Associates LLP"])
    assert f1_fuzzy == 1.0
    # Partial overlap -> strictly between 0 and 1.
    partial = set_overlap_f1(["Customer A"], ["Customer A", "Customer B"])
    assert 0.0 < partial < 1.0
    # Empty pred but non-empty gold -> 0.0.
    assert set_overlap_f1([], ["Customer A"]) == 0.0
    # score_field dispatches set on field_type.
    row = {
        "field_key": "customer_concentration",
        "field_type": "set",
        "gold_value": ["Customer A", "Customer B"],
    }
    assert score_field(row, ["Customer A", "Customer B"]) == 1.0


def test_refusal_scored_not_dropped() -> None:
    """A refusal where gold says absent scores as correct, not dropped (D3-03)."""
    from agent.schemas import RefusalResponse

    refusal = RefusalResponse(
        reason="unsupported_claim",
        explanation="Not disclosed in DRHP",
    )
    # not_disclosed gold + a stored RefusalResponse -> CORRECT.
    assert refusal_matches_absence(None, refusal) is True
    assert refusal_matches_absence("not_disclosed", refusal) is True
    # A non-refusal prediction against a not_disclosed gold -> NOT correct.
    assert refusal_matches_absence(None, 42.0) is False
    # A refusal against a disclosed gold -> NOT correct (extractor wrongly refused).
    assert refusal_matches_absence(3.4, refusal) is False

    # score_field keeps the not_disclosed cell in the denominator: a refusal
    # prediction scores 1.0, a wrong value scores 0.0 (neither is dropped).
    row_numeric_absent = {
        "field_key": "promoter_pledge_pct",
        "field_type": "numeric",
        "gold_value": None,
    }
    assert score_field(row_numeric_absent, refusal) == 1.0
    assert score_field(row_numeric_absent, 12.0) == 0.0

    row_set_absent = {
        "field_key": "customer_concentration",
        "field_type": "set",
        "gold_value": "not_disclosed",
    }
    assert score_field(row_set_absent, refusal) == 1.0


def test_bucket_split() -> None:
    """F1 is reported separately per confidence bucket (high/med/low, D3-04)."""
    # scored rows: (confidence_bucket, score). A not_disclosed/None bucket is its
    # own group — never silently merged or dropped.
    scored = [
        {"confidence_bucket": "high", "score": 1.0},
        {"confidence_bucket": "high", "score": 0.0},
        {"confidence_bucket": "medium", "score": 1.0},
        {"confidence_bucket": None, "score": 1.0},
    ]
    buckets = bucket_split(scored)
    assert buckets["high"]["n"] == 2
    assert buckets["high"]["mean_score"] == 0.5
    assert buckets["medium"]["n"] == 1
    assert buckets["medium"]["mean_score"] == 1.0
    # The None/not-disclosed bucket is preserved (D3-03 — not dropped).
    assert "not_disclosed" in buckets
    assert buckets["not_disclosed"]["n"] == 1
    assert buckets["not_disclosed"]["mean_score"] == 1.0
