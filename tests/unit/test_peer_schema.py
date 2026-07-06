"""
Unit test — PeerRecord round-trips with the {"refusal": ...} discriminator on the
peer_set value; each (company, metric) cell carries per-cell source + as_of
provenance; a fully-missing cell is None (renders "—"); a negative/undefined P/E
carries the NM sentinel; unknown metric/source keys are rejected.

Requirement: PEER-01/PEER-02, D4-05/D4-06. This mirrors tests/unit/test_redflag_schema.py
(the union-discriminator codec pattern) and pins Task 1's schema contract NOW.
"""
from __future__ import annotations

import pytest

from agent.peer_schema import (
    PEER_METRIC_KEYS,
    PeerCell,
    PeerCompany,
    PeerMetric,
    PeerRecord,
)
from agent.schemas import (
    Claim,
    GroundedAnswer,
    RefusalResponse,
    RetrievedChunkRef,
)


def _grounded_peer_set(claim_id: str = "c_peer01") -> GroundedAnswer:
    """A minimal valid cited GroundedAnswer naming the DRHP's listed peers."""
    span = "Comparison with listed industry peers: Zomato Limited"
    source = RetrievedChunkRef(
        chunk_id="chunk_peer_001",
        page_start=118,
        page_end=118,
        printed_page_label="118",
        section="Basis for Issue Price",
        score=0.83,
        verbatim_span=span,
        span_offsets=(0, len(span)),
    )
    claim = Claim(
        claim_id=claim_id,
        text="The company names Zomato Limited as a listed peer",
        source_chunk_id="chunk_peer_001",
        drhp_page=118,
        section="Basis for Issue Price",
        verbatim_span=span,
        span_offsets=(0, len(span)),
        sources=[source],
    )
    return GroundedAnswer(
        answer_prose=f"The company names Zomato Limited as a listed peer {{{{{claim_id}}}}}.",
        claims=[claim],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def _record() -> PeerRecord:
    return PeerRecord(
        drhp_id="swiggy_2024_11",
        computed_at="2026-07-06T00:00:00Z",
        as_of="2026-07-06",
        peer_set=_grounded_peer_set(),
        companies=[
            PeerCompany(
                name="Swiggy Limited",
                is_ipo=True,
                metrics=[
                    # P/E undefined (loss-making) -> NM sentinel, no fabricated value
                    PeerMetric(
                        metric="pe",
                        current=PeerCell(not_meaningful=True, source="y", as_of="current"),
                        drhp_date=None,
                    ),
                    PeerMetric(
                        metric="pb",
                        current=PeerCell(value=9.4, source="s", as_of="current"),
                        drhp_date=PeerCell(value=7.1, source="d", as_of="drhp_date"),
                    ),
                    # EV/EBITDA sourced from no source -> honest "—"
                    PeerMetric(
                        metric="ev_ebitda",
                        current=PeerCell(),
                        drhp_date=None,
                    ),
                    PeerMetric(
                        metric="roe",
                        current=PeerCell(value=-12.3, source="y", as_of="current"),
                        drhp_date=None,
                    ),
                ],
            ),
            PeerCompany(
                name="Zomato Limited",
                is_ipo=False,
                metrics=[
                    PeerMetric(
                        metric="pe",
                        current=PeerCell(value=312.5, source="s", as_of="current"),
                    ),
                    PeerMetric(
                        metric="roe",
                        current=PeerCell(value=1.5, source="y", as_of="current"),
                    ),
                ],
            ),
        ],
    )


def test_peer_record_roundtrip_grounded() -> None:
    """A PeerRecord with a grounded peer_set survives from_json(to_json()) with
    the union reconstructed as a GroundedAnswer and every cell's provenance intact."""
    rec = _record()
    restored = PeerRecord.from_json(rec.to_json())

    assert restored.drhp_id == "swiggy_2024_11"
    assert restored.as_of == "2026-07-06"

    # peer_set reconstructs as a cited GroundedAnswer (PEER-01)
    assert isinstance(restored.peer_set, GroundedAnswer)
    assert restored.peer_set.claims[0].claim_id == "c_peer01"
    assert restored.peer_set.claims[0].drhp_page == 118

    # companies + is_ipo flag survive
    assert [c.name for c in restored.companies] == ["Swiggy Limited", "Zomato Limited"]
    assert restored.companies[0].is_ipo is True
    assert restored.companies[1].is_ipo is False

    # per-cell provenance: value + source + as_of round-trip
    swiggy = restored.companies[0]
    pb = next(m for m in swiggy.metrics if m.metric == "pb")
    assert pb.current.value == 9.4
    assert pb.current.source == "s"
    assert pb.current.as_of == "current"
    # BOTH dimensions where available: DRHP-date cell present + labelled
    assert pb.drhp_date is not None
    assert pb.drhp_date.value == 7.1
    assert pb.drhp_date.source == "d"
    assert pb.drhp_date.as_of == "drhp_date"


def test_missing_cell_is_none_renders_emdash() -> None:
    """A fully-missing cell is PeerCell() with value None (renders '—'), never
    interpolated or zeroed (D4-05 honest gap)."""
    rec = PeerRecord.from_json(_record().to_json())
    swiggy = rec.companies[0]
    ev = next(m for m in swiggy.metrics if m.metric == "ev_ebitda")
    assert ev.current.value is None
    assert ev.current.source is None
    assert ev.current.not_meaningful is False


def test_nm_sentinel_for_undefined_pe() -> None:
    """A negative/undefined P/E carries a not_meaningful sentinel distinguishable
    from a real value AND from a missing cell (the NM render)."""
    rec = PeerRecord.from_json(_record().to_json())
    swiggy = rec.companies[0]
    pe = next(m for m in swiggy.metrics if m.metric == "pe")
    assert pe.current.not_meaningful is True
    assert pe.current.value is None  # NM is not a fabricated number
    # a source flag can still record which source was consulted
    assert pe.current.source == "y"


def test_refusal_peer_set_is_empty_state() -> None:
    """When the DRHP names no peers, peer_set is a RefusalResponse (D4-06 honest
    empty-state) reconstructed via the {'refusal': ...} discriminator — never a
    fabricated set."""
    rec = PeerRecord(
        drhp_id="swiggy_2024_11",
        computed_at="2026-07-06T00:00:00Z",
        as_of="2026-07-06",
        peer_set=RefusalResponse(
            reason="low_retrieval_score",
            explanation="This DRHP disclosed no listed-peer comparison.",
        ),
        companies=[],
    )
    restored = PeerRecord.from_json(rec.to_json())
    assert isinstance(restored.peer_set, RefusalResponse)
    assert restored.peer_set.explanation == "This DRHP disclosed no listed-peer comparison."
    assert restored.companies == []


def test_unknown_metric_key_rejected() -> None:
    """A PeerMetric with a key outside the locked 4-key allow-list raises."""
    with pytest.raises(ValueError):
        PeerMetric(metric="bogus_ratio", current=PeerCell(value=1.0))

    assert PEER_METRIC_KEYS == {"pe", "pb", "ev_ebitda", "roe"}


def test_unknown_source_flag_rejected() -> None:
    """A PeerCell with a source flag outside the locked ladder ('s','y','n','d')
    is rejected (only the source-priority ladder + DRHP flag are legal)."""
    with pytest.raises(ValueError):
        PeerCell(value=1.0, source="x", as_of="current")


def test_imports_grounded_answer_from_agent_schemas() -> None:
    """peer_schema reuses agent.schemas.GroundedAnswer/RefusalResponse verbatim
    (the cross-phase locked claim_id contract) — it does not redefine them."""
    import agent.peer_schema as ps
    import agent.schemas as schemas

    assert ps.GroundedAnswer is schemas.GroundedAnswer
    assert ps.RefusalResponse is schemas.RefusalResponse
