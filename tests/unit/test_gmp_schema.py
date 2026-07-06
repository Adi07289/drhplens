"""
Unit test — GmpRecord round-trips its multi-source quotes, derives the spread
(min/max/n) across aggregators, and treats absent-GMP (quotes == []) and
single-source GMP (len(quotes) == 1) as FIRST-CLASS states — never a fabricated
number, never a zero.

Requirement: GMP-01 (read-only multi-source GMP with caveats). This mirrors the
union-discriminator codec shape of tests/unit/test_redflag_schema.py /
tests/unit/test_peer_schema.py and pins Task 1's schema contract NOW.

Isolation (GMP-02, D4-03) is pinned separately in tests/unit/test_gmp_isolation.py.
"""
from __future__ import annotations

from agent.gmp_schema import GmpQuote, GmpRecord, GmpSpread


def _multi_source_record() -> GmpRecord:
    """A GmpRecord carrying a 3-aggregator spread (the disagreement signal, D4-01)."""
    return GmpRecord(
        drhp_id="hyundai_2024_10",
        computed_at="2026-07-06T00:00:00Z",
        as_of="2024-10-14",
        quotes=[
            GmpQuote(source="investorgain", value=25.0, as_of="2024-10-14"),
            GmpQuote(source="ipowatch", value=67.0, as_of="2024-10-14"),
            GmpQuote(source="ipocentral", value=50.0, as_of="2024-10-13"),
        ],
    )


def test_record_roundtrips_multi_source_quotes() -> None:
    """A multi-source GmpRecord survives from_json(to_json()) with every quote's
    source/value/as_of intact — the aggregator SPREAD is preserved (D4-01)."""
    rec = _multi_source_record()
    restored = GmpRecord.from_json(rec.to_json())

    assert restored.drhp_id == "hyundai_2024_10"
    assert restored.as_of == "2024-10-14"
    assert len(restored.quotes) == 3
    assert [q.source for q in restored.quotes] == [
        "investorgain",
        "ipowatch",
        "ipocentral",
    ]
    assert [q.value for q in restored.quotes] == [25.0, 67.0, 50.0]
    assert restored.quotes[2].as_of == "2024-10-13"


def test_spread_derives_min_max_n_across_sources() -> None:
    """spread() returns the min/max/n over the quotes — the honest divergence
    range across aggregators (D4-01)."""
    rec = _multi_source_record()
    spread = rec.spread()
    assert isinstance(spread, GmpSpread)
    assert spread.low == 25.0
    assert spread.high == 67.0
    assert spread.n == 3


def test_spread_roundtrips_through_serialization() -> None:
    """The spread derived after from_json matches the pre-serialization spread."""
    rec = _multi_source_record()
    restored = GmpRecord.from_json(rec.to_json())
    assert restored.spread() == rec.spread()


def test_absent_gmp_is_first_class_empty_state() -> None:
    """quotes == [] is the honest absent-GMP state (the COMMON case for
    already-listed catalogue IPOs) — NOT an error, NOT a fabricated zero. It
    round-trips and reports no spread (no cross-source check available)."""
    rec = GmpRecord(
        drhp_id="swiggy_2024_11",
        computed_at="2026-07-06T00:00:00Z",
        as_of="2026-07-06",
        quotes=[],
    )
    restored = GmpRecord.from_json(rec.to_json())

    assert restored.quotes == []
    assert restored.is_absent is True
    assert restored.is_single_source is False
    # no fabricated zero — the record simply carries no quotes
    assert restored.spread() is None


def test_single_source_is_first_class_state_with_no_spread() -> None:
    """len(quotes) == 1 is the single-source state — a valid, honest record with
    NO cross-source spread ('Only one source reported — no cross-source check
    available'). spread() is None because a spread needs >= 2 sources."""
    rec = GmpRecord(
        drhp_id="hyundai_2024_10",
        computed_at="2026-07-06T00:00:00Z",
        as_of="2024-10-14",
        quotes=[GmpQuote(source="investorgain", value=42.0, as_of="2024-10-14")],
    )
    restored = GmpRecord.from_json(rec.to_json())

    assert len(restored.quotes) == 1
    assert restored.is_absent is False
    assert restored.is_single_source is True
    assert restored.spread() is None
    # the single reported value is preserved, never averaged away or zeroed
    assert restored.quotes[0].value == 42.0


def test_two_source_spread_is_available() -> None:
    """Exactly two sources IS a cross-source check — spread() returns low/high/n=2."""
    rec = GmpRecord(
        drhp_id="hyundai_2024_10",
        computed_at="2026-07-06T00:00:00Z",
        as_of="2024-10-14",
        quotes=[
            GmpQuote(source="investorgain", value=30.0, as_of="2024-10-14"),
            GmpQuote(source="ipowatch", value=55.0, as_of="2024-10-14"),
        ],
    )
    spread = rec.spread()
    assert isinstance(spread, GmpSpread)
    assert spread.low == 30.0
    assert spread.high == 55.0
    assert spread.n == 2


def test_to_dict_shape_is_diff_reviewable() -> None:
    """to_dict emits the flat on-disk shape (drhp_id/computed_at/as_of/quotes);
    to_json is indent=2 for a diff-reviewable committed cache."""
    rec = _multi_source_record()
    d = rec.to_dict()
    assert set(d.keys()) == {"drhp_id", "computed_at", "as_of", "quotes"}
    assert d["quotes"][0] == {
        "source": "investorgain",
        "value": 25.0,
        "as_of": "2024-10-14",
    }
    assert "\n  " in rec.to_json()  # indent=2
