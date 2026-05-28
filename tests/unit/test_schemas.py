"""
TDD Wave 1 — agent/schemas.py: Pydantic v2 schema contract.

Validates: claim_id regex, span_offsets ordering, source min_length,
GroundedAnswer unique claim_ids, RefusalReason enum vocabulary,
RefusalResponse max_length=3 reformulation_suggestions, GraphState keys.

SKELETON §B contract: the claim_id pattern r'^c_[a-z0-9]{6,16}$' and all
exported class names (RetrievedChunkRef, Claim, GroundedAnswer, RefusalReason,
RefusalResponse) are the cross-phase lock Phase 3 METHOD-01 consumes verbatim.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.schemas import (
    Claim,
    GroundedAnswer,
    RefusalReason,
    RefusalResponse,
    RetrievedChunkRef,
)


# ---------------------------------------------------------------------------
# Helpers — minimal valid objects for composing test inputs
# ---------------------------------------------------------------------------

def _make_valid_ref(**kwargs) -> RetrievedChunkRef:
    defaults: dict = {
        "chunk_id": "abc123",
        "page_start": 1,
        "page_end": 2,
        "section": "Risk Factors",
    }
    defaults.update(kwargs)
    return RetrievedChunkRef(**defaults)


def _make_valid_claim(**kwargs) -> Claim:
    ref = _make_valid_ref()
    defaults: dict = {
        "claim_id": "c_4f3a8b",
        "text": "Promoters hold 31.4% post-issue.",
        "source_chunk_id": "abc123",
        "drhp_page": 1,
        "section": "Risk Factors",
        "verbatim_span": "Promoters hold 31.4% post-issue.",
        "span_offsets": (0, 34),
        "sources": [ref],
    }
    defaults.update(kwargs)
    return Claim(**defaults)


# ---------------------------------------------------------------------------
# Task 1 tests: claim_id pattern enforcement
# ---------------------------------------------------------------------------

def test_claim_id_pattern_enforced() -> None:
    """claim_id must match r'^c_[a-z0-9]{6,16}$'; schema rejects invalid patterns."""
    ref = _make_valid_ref()

    # Valid claim_id — should succeed
    claim = _make_valid_claim(claim_id="c_4f3a8b")
    assert claim.claim_id == "c_4f3a8b"

    # Invalid pattern — should raise
    with pytest.raises(ValidationError):
        _make_valid_claim(claim_id="bad")


def test_claim_id_uppercase_rejected() -> None:
    """claim_id must be fully lowercase; uppercase characters are rejected."""
    with pytest.raises(ValidationError):
        _make_valid_claim(claim_id="c_4F3A")


def test_claim_id_too_short_rejected() -> None:
    """claim_id suffix must be at least 6 characters; fewer is rejected."""
    with pytest.raises(ValidationError):
        _make_valid_claim(claim_id="c_4f3")


def test_claim_id_too_long_rejected() -> None:
    """claim_id suffix must be at most 16 characters; 17 chars is rejected."""
    with pytest.raises(ValidationError):
        _make_valid_claim(claim_id="c_" + "a" * 17)


def test_claim_id_valid_boundary_6_chars() -> None:
    """Exactly 6 characters after c_ is valid (lower boundary)."""
    claim = _make_valid_claim(claim_id="c_abcdef")
    assert claim.claim_id == "c_abcdef"


def test_claim_id_valid_boundary_16_chars() -> None:
    """Exactly 16 characters after c_ is valid (upper boundary)."""
    claim = _make_valid_claim(claim_id="c_" + "a" * 16)
    assert claim.claim_id == "c_" + "a" * 16


# ---------------------------------------------------------------------------
# Task 1 tests: source min_length
# ---------------------------------------------------------------------------

def test_claim_requires_at_least_one_source() -> None:
    """Claim.sources must have >= 1 entry; empty list raises ValidationError."""
    with pytest.raises(ValidationError):
        _make_valid_claim(sources=[])


def test_claim_accepts_multiple_sources() -> None:
    """Claim.sources can hold multiple RetrievedChunkRef instances."""
    ref1 = _make_valid_ref(chunk_id="chunk_01")
    ref2 = _make_valid_ref(chunk_id="chunk_02", page_start=3, page_end=4)
    claim = _make_valid_claim(sources=[ref1, ref2])
    assert len(claim.sources) == 2


# ---------------------------------------------------------------------------
# Task 1 tests: span_offsets validation
# ---------------------------------------------------------------------------

def test_retrieved_chunk_ref_span_offsets_valid_tuple() -> None:
    """span_offsets=(0, 100) is accepted."""
    ref = _make_valid_ref(span_offsets=(0, 100))
    assert ref.span_offsets == (0, 100)


def test_retrieved_chunk_ref_span_offsets_equal_is_valid() -> None:
    """span_offsets=(50, 50) is accepted (zero-length span)."""
    ref = _make_valid_ref(span_offsets=(50, 50))
    assert ref.span_offsets == (50, 50)


def test_retrieved_chunk_ref_span_offsets_inverted_rejected() -> None:
    """span_offsets=(100, 0) must raise ValidationError (start > end)."""
    with pytest.raises(ValidationError):
        _make_valid_ref(span_offsets=(100, 0))


def test_retrieved_chunk_ref_span_offsets_none_accepted() -> None:
    """span_offsets=None is accepted (optional field)."""
    ref = _make_valid_ref(span_offsets=None)
    assert ref.span_offsets is None


# ---------------------------------------------------------------------------
# Task 1 tests: GroundedAnswer
# ---------------------------------------------------------------------------

def test_grounded_answer_serializes_to_json() -> None:
    """Round-trip model_dump_json() -> model_validate_json() returns equal instance."""
    claim = _make_valid_claim()
    answer = GroundedAnswer(
        answer_prose="Promoters hold {{c_4f3a8b}} post-issue.",
        claims=[claim],
    )
    json_str = answer.model_dump_json()
    restored = GroundedAnswer.model_validate_json(json_str)
    assert restored == answer


def test_grounded_answer_sub_question_lists_default_empty() -> None:
    """sub_question_addressed and sub_question_unaddressed default to []."""
    claim = _make_valid_claim()
    answer = GroundedAnswer(
        answer_prose="Test answer {{c_4f3a8b}}.",
        claims=[claim],
    )
    assert answer.sub_question_addressed == []
    assert answer.sub_question_unaddressed == []


def test_grounded_answer_unique_claim_ids_enforced() -> None:
    """Duplicate claim_ids within a GroundedAnswer raise ValidationError."""
    claim1 = _make_valid_claim(claim_id="c_4f3a8b")
    # Build second claim with same ID but different content
    ref2 = _make_valid_ref(chunk_id="chunk_99")
    claim2 = Claim(
        claim_id="c_4f3a8b",  # duplicate!
        text="Different text.",
        source_chunk_id="chunk_99",
        drhp_page=5,
        section="Use of Proceeds",
        verbatim_span="Different text.",
        span_offsets=(0, 15),
        sources=[ref2],
    )
    with pytest.raises(ValidationError):
        GroundedAnswer(
            answer_prose="{{c_4f3a8b}} {{c_4f3a8b}}",
            claims=[claim1, claim2],
        )


# ---------------------------------------------------------------------------
# Task 1 tests: RefusalReason locked vocabulary
# ---------------------------------------------------------------------------

def test_refusal_reason_enum_values() -> None:
    """RefusalReason Literal values are exactly the four locked values.

    Wave 3 nodes branch on these exact strings; adding/removing values here
    requires updating every conditional edge in agent/graph.py.
    """
    import typing

    args = typing.get_args(RefusalReason)
    assert set(args) == {
        "low_retrieval_score",
        "unsupported_claim",
        "banned_token",
        "infrastructure_error",
    }, f"Unexpected RefusalReason values: {args}"


# ---------------------------------------------------------------------------
# Task 1 tests: RefusalResponse
# ---------------------------------------------------------------------------

def test_refusal_response_max_three_suggestions() -> None:
    """reformulation_suggestions max_length=3; four items raises ValidationError."""
    with pytest.raises(ValidationError):
        RefusalResponse(
            reason="low_retrieval_score",
            explanation="Not grounded.",
            reformulation_suggestions=["a", "b", "c", "d"],  # 4 > max 3
        )


def test_refusal_response_accepts_three_suggestions() -> None:
    """Three reformulation suggestions are accepted (at the max boundary)."""
    r = RefusalResponse(
        reason="banned_token",
        explanation="Banned token detected.",
        reformulation_suggestions=["q1", "q2", "q3"],
    )
    assert len(r.reformulation_suggestions) == 3


def test_refusal_response_default_empty_suggestions() -> None:
    """reformulation_suggestions defaults to []."""
    r = RefusalResponse(
        reason="infrastructure_error",
        explanation="LLM timeout.",
    )
    assert r.reformulation_suggestions == []


# ---------------------------------------------------------------------------
# Task 1 tests: GraphState shape
# ---------------------------------------------------------------------------

def test_graph_state_typeddict_shape() -> None:
    """GraphState __annotations__ contains all required keys for Wave 3 consumption."""
    from agent.state import GraphState

    required_keys = {
        "question",
        "retrieved_chunks",
        "reranked_top_k",
        "gate1_passed",
        "gate1_max_score",
        "sub_questions",
        "grounded_answer",
        "scrub_passed",
        "regenerate_attempts",
        "all_claims_grounded",
        "cite_check_failures",
        "refusal",
    }
    actual_keys = set(GraphState.__annotations__.keys())
    missing = required_keys - actual_keys
    assert not missing, f"GraphState is missing required keys: {missing}"
