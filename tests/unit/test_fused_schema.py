"""Contract tests for Phase 6.3 Plan 01 — ToolClaim sibling + FusedAnswer union (D-03).

RESEARCH caveat (e): tool-derived numbers (peer / forecast / red-flag) have NO DRHP
chunk, page, or verbatim span, so forcing them through ``Claim`` (or a ``Claim``
subclass) would fabricate DRHP-span fields and violate the honesty invariant. The
resolution is a DISCRIMINATED UNION: ``Claim`` stays byte-identical for DRHP-grounded
claims, and a SIBLING ``ToolClaim`` (its own BaseModel) carries tool provenance. A
``FusedAnswer`` then carries ``claims: list[Claim | ToolClaim]``.

These tests lock:
  - ToolClaim reuses the EXACT locked ``^c_[a-z0-9]{6,16}$`` claim_id regex.
  - ToolClaim fabricates NO DRHP-span fields (no drhp_page/verbatim_span/span_offsets/sources).
  - FusedAnswer parses a mixed [Claim, ToolClaim] list, preserving each type.
  - FusedAnswer ports the unique-within-answer validator across the whole union.
  - The untouched ``Claim`` still enforces its span_offsets start<=end invariant.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.schemas import Claim, FusedAnswer, RetrievedChunkRef, ToolClaim


def make_chunk_ref(**overrides) -> RetrievedChunkRef:
    base = dict(chunk_id="chunk-1", page_start=10, page_end=11, section="Risk Factors")
    base.update(overrides)
    return RetrievedChunkRef(**base)


def make_claim(claim_id: str = "c_abc123", span_offsets=None, **overrides) -> Claim:
    base = dict(
        claim_id=claim_id,
        text="Revenue was 100 cr in FY24.",
        source_chunk_id="chunk-1",
        drhp_page=10,
        section="Risk Factors",
        verbatim_span="Revenue was 100 cr in FY24",
        span_offsets=[0, 18] if span_offsets is None else span_offsets,
        sources=[make_chunk_ref()],
    )
    base.update(overrides)
    return Claim(**base)


def make_tool_claim(claim_id: str = "c_def456", **overrides) -> ToolClaim:
    base = dict(
        claim_id=claim_id,
        text="Median peer P/E is 28.5x.",
        value=28.5,
        source_tool="query_peers",
        source_record_id="data/peers/swiggy_2024_11.json#median_pe",
    )
    base.update(overrides)
    return ToolClaim(**base)


class TestToolClaimContract:
    def test_toolclaim_accepts_valid_construction(self):
        tc = make_tool_claim()
        assert tc.claim_id == "c_def456"
        assert tc.value == 28.5
        assert tc.source_tool == "query_peers"
        assert tc.source_record_id.startswith("data/peers/")

    def test_toolclaim_value_accepts_str_for_not_disclosed(self):
        tc = make_tool_claim(value="not disclosed")
        assert tc.value == "not disclosed"

    def test_toolclaim_rejects_malformed_claim_id(self):
        with pytest.raises(ValidationError):
            make_tool_claim(claim_id="BAD")

    def test_toolclaim_reuses_exact_claim_id_pattern(self):
        # too-short (4 chars after 'c_') rejected; 6-char boundary accepted —
        # the identical ^c_[a-z0-9]{6,16}$ contract as Claim so the C2 renderer resolves it.
        with pytest.raises(ValidationError):
            make_tool_claim(claim_id="c_abcd")
        assert make_tool_claim(claim_id="c_abcdef").claim_id == "c_abcdef"

    def test_toolclaim_rejects_uppercase_claim_id(self):
        with pytest.raises(ValidationError):
            make_tool_claim(claim_id="c_ABC123")

    def test_toolclaim_rejects_unknown_source_tool(self):
        with pytest.raises(ValidationError):
            make_tool_claim(source_tool="query_gmp")

    def test_toolclaim_has_no_fabricated_drhp_span_fields(self):
        # Honesty invariant: a tool number must not carry DRHP-span-shaped fields.
        for banned in (
            "drhp_page",
            "verbatim_span",
            "span_offsets",
            "sources",
            "source_chunk_id",
        ):
            assert banned not in ToolClaim.model_fields

    def test_toolclaim_is_not_a_claim_subclass(self):
        assert not issubclass(ToolClaim, Claim)


class TestFusedAnswerUnion:
    def test_parses_mixed_claim_and_toolclaim_preserving_types(self):
        claim = make_claim(claim_id="c_aaa111")
        tool = make_tool_claim(claim_id="c_bbb222")
        fa = FusedAnswer(
            answer_prose="The DRHP says {{c_aaa111}}; peers imply {{c_bbb222}}.",
            claims=[claim, tool],
        )
        assert len(fa.claims) == 2
        assert isinstance(fa.claims[0], Claim)
        assert isinstance(fa.claims[1], ToolClaim)
        # both are render-addressable by claim_id
        assert {c.claim_id for c in fa.claims} == {"c_aaa111", "c_bbb222"}
        assert fa.is_partial is False
        assert fa.unaddressed == []

    def test_is_partial_and_unaddressed_carry_through(self):
        fa = FusedAnswer(
            answer_prose="Here is what I found {{c_abc123}}.",
            claims=[make_claim()],
            is_partial=True,
            unaddressed=["forecast band unavailable for this IPO"],
        )
        assert fa.is_partial is True
        assert fa.unaddressed == ["forecast band unavailable for this IPO"]

    def test_rejects_duplicate_claim_ids_across_the_union(self):
        claim = make_claim(claim_id="c_dupe12")
        tool = make_tool_claim(claim_id="c_dupe12")
        with pytest.raises(ValidationError):
            FusedAnswer(answer_prose="{{c_dupe12}}", claims=[claim, tool])


class TestLockedClaimInvariantsUntouched:
    def test_claim_span_offsets_start_gt_end_still_raises(self):
        with pytest.raises(ValidationError):
            make_claim(span_offsets=[5, 2])

    def test_claim_id_regex_still_rejects_malformed(self):
        with pytest.raises(ValidationError):
            make_claim(claim_id="BAD")

    def test_claim_still_requires_at_least_one_source(self):
        # PITFALL P18 antibody unchanged: sources min_length=1.
        with pytest.raises(ValidationError):
            make_claim(sources=[])
