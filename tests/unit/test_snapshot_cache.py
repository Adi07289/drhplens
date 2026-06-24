"""
Unit test — data/snapshots/<drhp_id>.json round-trips; carries claim_ids;
scrubber-clean (no threat for the round-trip; tampering threat covered by
T-02-01-adjacent posture — committed JSON is trusted config).

Requirement: SNAP-02..07. Threat: none directly (snapshot-cache poisoning is
mitigated by the existing scrubber + cite-check at pre-compute time, per
02-RESEARCH.md Security Domain table).
Secure behavior: data/snapshots/<drhp_id>.json round-trips a serialized
GroundedAnswer/RefusalResponse losslessly; carries claim_ids; scrubber-clean.

Wave 3 implementation (02-04-PLAN.md Task 1).
"""
from __future__ import annotations

from agent.schemas import Claim, GroundedAnswer, RefusalResponse, RetrievedChunkRef
from agent.snapshot_schema import SnapshotRecord
from pipelines.snapshot import load_snapshot
from pipelines.snapshot_queries import SNAPSHOT_QUERIES


def _make_chunk_ref() -> RetrievedChunkRef:
    return RetrievedChunkRef(
        chunk_id="chunk_001",
        page_start=5,
        page_end=6,
        printed_page_label="5",
        section="Issue Details",
        score=0.92,
        verbatim_span="The total issue size is ₹11,300 crores",
        span_offsets=(0, 38),
    )


def _make_claim(claim_id: str = "c_abc123") -> Claim:
    return Claim(
        claim_id=claim_id,
        text="The issue size is ₹11,300 cr",
        source_chunk_id="chunk_001",
        drhp_page=5,
        section="Issue Details",
        verbatim_span="The total issue size is ₹11,300 crores",
        span_offsets=(0, 38),
        sources=[_make_chunk_ref()],
    )


def _make_grounded_answer(claim_id: str = "c_abc123") -> GroundedAnswer:
    return GroundedAnswer(
        answer_prose=f"The issue size is ₹11,300 cr {{{{{claim_id}}}}}.",
        claims=[_make_claim(claim_id)],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def _make_refusal() -> RefusalResponse:
    return RefusalResponse(
        reason="unsupported_claim",
        explanation="This DRHP does not disclose any promoter pledging.",
        reformulation_suggestions=["Who are the promoters?"],
    )


def test_snapshot_cache_round_trips_grounded_answer() -> None:
    """A field holding a GroundedAnswer model_dumps to JSON and
    model_validates back losslessly (claim_ids, claims, span_offsets preserved)."""
    ga = _make_grounded_answer()
    record = SnapshotRecord(
        drhp_id="test_ipo_2026_01",
        computed_at="2026-06-23T00:00:00Z",
        fields={"metadata": ga},
        ofs_fresh=None,
    )

    text = record.to_json()
    restored = SnapshotRecord.from_json(text)

    restored_ga = restored.fields["metadata"]
    assert isinstance(restored_ga, GroundedAnswer)
    assert restored_ga.answer_prose == ga.answer_prose
    assert len(restored_ga.claims) == 1
    assert restored_ga.claims[0].claim_id == "c_abc123"
    assert restored_ga.claims[0].span_offsets == (0, 38)
    assert restored_ga.claims[0].sources[0].chunk_id == "chunk_001"


def test_snapshot_cache_round_trips_refusal_response() -> None:
    """A field holding a RefusalResponse round-trips losslessly
    (reason/explanation preserved)."""
    refusal = _make_refusal()
    record = SnapshotRecord(
        drhp_id="test_ipo_2026_01",
        computed_at="2026-06-23T00:00:00Z",
        fields={"promoter": refusal},
        ofs_fresh=None,
    )

    text = record.to_json()
    restored = SnapshotRecord.from_json(text)

    restored_refusal = restored.fields["promoter"]
    assert isinstance(restored_refusal, RefusalResponse)
    assert restored_refusal.reason == "unsupported_claim"
    assert restored_refusal.explanation == refusal.explanation
    assert restored_refusal.reformulation_suggestions == ["Who are the promoters?"]


def test_load_snapshot_reads_seed_swiggy_json() -> None:
    """load_snapshot("swiggy_2024_11") reads data/snapshots/swiggy_2024_11.json
    into a SnapshotRecord; each of the 6 field keys resolves to either a
    GroundedAnswer or a RefusalResponse."""
    record = load_snapshot("swiggy_2024_11")

    assert record.drhp_id == "swiggy_2024_11"
    assert set(record.fields.keys()) == set(SNAPSHOT_QUERIES.keys())

    for key, value in record.fields.items():
        assert isinstance(value, (GroundedAnswer, RefusalResponse)), (
            f"field {key!r} resolved to {type(value)}, expected GroundedAnswer or RefusalResponse"
        )

    # SNAP-07 pledging honesty: Swiggy's seed stores promoter as an honest refusal.
    assert isinstance(record.fields["promoter"], RefusalResponse)


def test_snapshot_queries_has_exactly_six_contract_keys() -> None:
    """SNAPSHOT_QUERIES has exactly the 6 keys: metadata, business, financials,
    risks, use_of_proceeds, promoter."""
    assert set(SNAPSHOT_QUERIES.keys()) == {
        "metadata",
        "business",
        "financials",
        "risks",
        "use_of_proceeds",
        "promoter",
    }
    for query in SNAPSHOT_QUERIES.values():
        assert isinstance(query, str)
        assert len(query) > 0
