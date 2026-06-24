"""
Unit test — OFS-vs-fresh % computed from use-of-proceeds; foregrounded;
neutral (no green/red) (no threat).

Requirement: SNAP-06. Threat: none (honesty-first / no-perf-badge UI invariant,
not a STRIDE threat).
Secure behavior: the offer-for-sale vs fresh-issue split is computed from the
use-of-proceeds snapshot field and rendered neutrally (D2-06) — no
winner/loser color coding.

Wave 3 implementation (02-04-PLAN.md Task 2).
"""
from __future__ import annotations

from agent.schemas import Claim, GroundedAnswer, RefusalResponse, RetrievedChunkRef
from pipelines.snapshot import compute_ofs_fresh


def _make_claim(claim_id: str, text: str, span: str) -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        source_chunk_id="chunk_001",
        drhp_page=95,
        section="Objects of the Offer",
        verbatim_span=span,
        span_offsets=(0, len(span)),
        sources=[
            RetrievedChunkRef(
                chunk_id="chunk_001",
                page_start=95,
                page_end=96,
                printed_page_label="93",
                section="Objects of the Offer",
                score=0.9,
                verbatim_span=span,
                span_offsets=(0, len(span)),
            )
        ],
    )


def _make_ga(prose: str, claim_text: str, span: str, claim_id: str = "c_split01") -> GroundedAnswer:
    return GroundedAnswer(
        answer_prose=f"{prose} {{{{{claim_id}}}}}.",
        claims=[_make_claim(claim_id, claim_text, span)],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def test_compute_ofs_fresh_returns_pair_summing_to_100() -> None:
    """compute_ofs_fresh(use_of_proceeds_field) returns {"ofs_pct": x,
    "fresh_pct": y} summing to 100 (within rounding)."""
    field = _make_ga(
        "The offer is 41% OFS and 59% fresh issue",
        "41% OFS and 59% fresh issue",
        "The Offer comprises 41% Offer for Sale and 59% Fresh Issue.",
    )

    result = compute_ofs_fresh(field)

    assert result is not None
    assert "ofs_pct" in result and "fresh_pct" in result
    assert abs((result["ofs_pct"] + result["fresh_pct"]) - 100.0) < 0.01
    assert result["ofs_pct"] == 41.0
    assert result["fresh_pct"] == 59.0


def test_compute_ofs_fresh_pure_ofs_yields_100_0() -> None:
    """A 100%-OFS input yields ofs_pct=100/fresh_pct=0."""
    field = _make_ga(
        "The entire offer is an Offer for Sale",
        "100% OFS, no fresh issue",
        "The Offer comprises 100% Offer for Sale.",
    )

    result = compute_ofs_fresh(field)

    assert result is not None
    assert result["ofs_pct"] == 100.0
    assert result["fresh_pct"] == 0.0


def test_compute_ofs_fresh_pure_fresh_yields_0_100() -> None:
    """A 100%-fresh input yields ofs_pct=0/fresh_pct=100 (no OFS, the other side)."""
    field = _make_ga(
        "The entire offer is a fresh issue",
        "100% fresh issue, no OFS",
        "The Offer comprises 100% Fresh Issue.",
    )

    result = compute_ofs_fresh(field)

    assert result is not None
    assert result["fresh_pct"] == 100.0
    assert result["ofs_pct"] == 0.0


def test_compute_ofs_fresh_no_verdict_field() -> None:
    """Values are plain numbers with NO red/green/verdict field (SNAP-06
    neutrality)."""
    field = _make_ga(
        "41% OFS and 59% fresh issue",
        "41% OFS and 59% fresh issue",
        "The Offer comprises 41% Offer for Sale and 59% Fresh Issue.",
    )

    result = compute_ofs_fresh(field)

    assert result is not None
    forbidden_keys = {"verdict", "color", "good", "bad", "warning", "severity", "status"}
    assert forbidden_keys.isdisjoint(result.keys())
    allowed_keys = {"ofs_pct", "fresh_pct", "source_claim_id"}
    assert set(result.keys()).issubset(allowed_keys)


def test_compute_ofs_fresh_returns_none_when_drhp_silent() -> None:
    """A RefusalResponse (DRHP did not disclose the split) yields None — the
    UI shows not-disclosed rather than a fabricated bar."""
    refusal = RefusalResponse(
        reason="unsupported_claim",
        explanation="This DRHP does not disclose a clear OFS/fresh split.",
        reformulation_suggestions=[],
    )

    result = compute_ofs_fresh(refusal)

    assert result is None


def test_compute_ofs_fresh_returns_none_when_field_is_none() -> None:
    """A missing use_of_proceeds field yields None, not a crash."""
    assert compute_ofs_fresh(None) is None
