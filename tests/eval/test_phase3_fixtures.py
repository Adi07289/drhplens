"""
Wave 0 fixture-contract test (03-01-PLAN Task 2) — exercises the shared Phase 3
fixtures in tests/eval/conftest.py so they are validated NOW, not only when the
downstream plans land. NOT skipped: this is the acceptance gate that
synthetic_redflag_record round-trips and the label/corpus fixtures have the
documented shape.
"""
from __future__ import annotations

from agent.redflag_schema import RankedRisk, RedFlagRecord
from agent.schemas import GroundedAnswer, RefusalResponse


def test_synthetic_redflag_record_roundtrips(
    synthetic_redflag_record: RedFlagRecord,
) -> None:
    """synthetic_redflag_record has >=1 GroundedAnswer field, >=1 RefusalResponse
    field, >=2 RankedRisk items, and round-trips through to_json/from_json."""
    rec = synthetic_redflag_record

    ga_fields = [
        f for f in rec.fields.values() if isinstance(f.value, GroundedAnswer)
    ]
    refusal_fields = [
        f for f in rec.fields.values() if isinstance(f.value, RefusalResponse)
    ]
    assert len(ga_fields) >= 1
    assert len(refusal_fields) >= 1
    assert len(rec.ranked_risks) >= 2
    assert all(isinstance(r, RankedRisk) for r in rec.ranked_risks)

    restored = RedFlagRecord.from_json(rec.to_json())
    assert restored.drhp_id == rec.drhp_id
    assert set(restored.fields) == set(rec.fields)
    assert isinstance(restored.fields["rpt_pct"].value, GroundedAnswer)
    assert isinstance(
        restored.fields["promoter_pledge_pct"].value, RefusalResponse
    )


def test_tiny_extraction_labels_shape(tiny_extraction_labels: list[dict]) -> None:
    """tiny_extraction_labels covers one numeric, one boolean, one set field,
    and one not-disclosed (gold None) row."""
    field_types = {row["field_type"] for row in tiny_extraction_labels}
    assert {"numeric", "boolean", "set"} <= field_types
    assert any(row["gold"] is None for row in tiny_extraction_labels)


def test_idf_corpus_3doc_shape(idf_corpus_3doc: list[str]) -> None:
    """idf_corpus_3doc has 3 docs; 2 share a boilerplate phrase, 1 is unique."""
    assert len(idf_corpus_3doc) == 3
    boilerplate = "subject to extensive government regulation"
    shared = [d for d in idf_corpus_3doc if boilerplate in d.lower()]
    assert len(shared) == 2
