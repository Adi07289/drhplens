"""
Unit test — the GMP precompute loop scrapes each public aggregator with per-source
failure isolation, assembles one GmpQuote per REACHABLE aggregator into a
GmpRecord (preserving their spread, D4-01), and treats absent-GMP (quotes == [])
and single-source GMP as first-class states — never a fabricated value, never a
zero. The allow-list gates the cache path (T-04-04-PATH).

Fully offline: every aggregator fetcher is monkeypatched — NO live network happens
under `pytest tests/unit` (CODE-NOW-DEFER; the live scrape is a deferred runbook
step). Isolation (GMP-02) is pinned separately in test_gmp_isolation.py.
"""
from __future__ import annotations

import pytest

import pipelines.gmp_sources as gs
from agent.gmp_schema import GmpQuote, GmpRecord

KNOWN_DRHP_ID = "hyundai_2024_10"
ABSENT_DRHP_ID = "swiggy_2024_11"


# ---------------------------------------------------------------------------
# Aggregator monkeypatch helpers (no live network)
# ---------------------------------------------------------------------------


def _patch_quotes(monkeypatch, investorgain, ipowatch, ipocentral) -> None:
    """Replace each aggregator fetcher with a canned GmpQuote|None or a raiser."""
    monkeypatch.setattr(gs, "investorgain_quote", investorgain, raising=True)
    monkeypatch.setattr(gs, "ipowatch_quote", ipowatch, raising=True)
    monkeypatch.setattr(gs, "ipocentral_quote", ipocentral, raising=True)


def _q(source: str, value: float):
    return lambda name: GmpQuote(source=source, value=value, as_of="2024-10-14")


def _none(name):
    return None


def _raise(name):
    raise RuntimeError("simulated aggregator failure")


# ---------------------------------------------------------------------------
# Precompute behaviour
# ---------------------------------------------------------------------------


def test_multi_source_spread_is_assembled(monkeypatch) -> None:
    """All three aggregators reporting → a 3-quote GmpRecord whose spread captures
    their disagreement (D4-01) — the values are kept SEPARATE, never averaged."""
    from pipelines import gmp

    _patch_quotes(
        monkeypatch,
        _q("investorgain", 25.0),
        _q("ipowatch", 67.0),
        _q("ipocentral", 50.0),
    )
    record = gmp.precompute_gmp(KNOWN_DRHP_ID, write=False)

    assert isinstance(record, GmpRecord)
    assert len(record.quotes) == 3
    assert {q.source for q in record.quotes} == {
        "investorgain",
        "ipowatch",
        "ipocentral",
    }
    spread = record.spread()
    assert spread is not None
    assert spread.low == 25.0
    assert spread.high == 67.0
    assert spread.n == 3


def test_single_source_is_first_class(monkeypatch) -> None:
    """Only one aggregator reporting → a valid single-source record (len==1) with
    NO cross-source spread — never fabricated up to a spread."""
    from pipelines import gmp

    _patch_quotes(monkeypatch, _q("investorgain", 42.0), _none, _none)
    record = gmp.precompute_gmp(KNOWN_DRHP_ID, write=False)

    assert len(record.quotes) == 1
    assert record.is_single_source is True
    assert record.spread() is None
    assert record.quotes[0].value == 42.0


def test_absent_gmp_is_first_class_empty_record(monkeypatch) -> None:
    """No aggregator reporting (the COMMON already-listed case) → quotes == [] —
    the honest absent-GMP state, NOT a zero, NOT an error."""
    from pipelines import gmp

    _patch_quotes(monkeypatch, _none, _none, _none)
    record = gmp.precompute_gmp(ABSENT_DRHP_ID, write=False)

    assert record.quotes == []
    assert record.is_absent is True
    assert record.spread() is None


def test_per_source_failure_is_isolated(monkeypatch) -> None:
    """One aggregator raising must NOT abort the batch and must NOT fabricate a
    value for it — the reachable aggregators still produce their quotes (P14)."""
    from pipelines import gmp

    _patch_quotes(monkeypatch, _q("investorgain", 30.0), _raise, _q("ipocentral", 55.0))
    record = gmp.precompute_gmp(KNOWN_DRHP_ID, write=False)

    sources = {q.source for q in record.quotes}
    assert sources == {"investorgain", "ipocentral"}  # the raiser contributed nothing
    assert "ipowatch" not in sources
    assert len(record.quotes) == 2


def test_path_gate_rejects_unknown_drhp_id() -> None:
    """precompute_gmp + load_gmp raise on a non-allow-listed drhp_id BEFORE forming
    any path (path-traversal control T-04-04-PATH)."""
    from pipelines import gmp

    with pytest.raises(ValueError):
        gmp.precompute_gmp("../etc/passwd", write=False)
    with pytest.raises(ValueError):
        gmp.load_gmp("../etc/passwd")


def test_load_known_but_uncached_raises_file_not_found() -> None:
    """A known catalogue id with no GMP cache raises FileNotFoundError (the gate
    passes, the path is formed, the file is simply absent)."""
    from pipelines import gmp

    with pytest.raises(FileNotFoundError):
        gmp.load_gmp("nykaa_2021_10")


def test_write_false_does_not_touch_disk(monkeypatch, tmp_path) -> None:
    """write=False computes the record without writing any file (offline tests)."""
    from pipelines import gmp

    monkeypatch.setattr(gmp, "GMP_DIR", tmp_path, raising=True)
    _patch_quotes(monkeypatch, _q("investorgain", 25.0), _none, _none)
    gmp.precompute_gmp(KNOWN_DRHP_ID, write=False)

    assert list(tmp_path.iterdir()) == []


def test_record_round_trips_via_load_gmp(monkeypatch, tmp_path) -> None:
    """precompute_gmp(write=True) then load_gmp reconstructs the same quotes."""
    from pipelines import gmp

    monkeypatch.setattr(gmp, "GMP_DIR", tmp_path, raising=True)
    _patch_quotes(
        monkeypatch,
        _q("investorgain", 25.0),
        _q("ipowatch", 67.0),
        _none,
    )
    written = gmp.precompute_gmp(KNOWN_DRHP_ID, write=True)
    loaded = gmp.load_gmp(KNOWN_DRHP_ID)

    assert loaded.drhp_id == written.drhp_id
    assert [(q.source, q.value) for q in loaded.quotes] == [
        (q.source, q.value) for q in written.quotes
    ]


# ---------------------------------------------------------------------------
# Seed fixtures (hand-seeded, committed, offline)
# ---------------------------------------------------------------------------


def test_absent_seed_fixture_loads_with_zero_quotes() -> None:
    """data/gmp/swiggy_2024_11.json = the absent-GMP state (already listed — the
    common case): loads, validates, and has zero quotes (an honest empty record)."""
    from pipelines import gmp

    record = gmp.load_gmp(ABSENT_DRHP_ID)
    assert isinstance(record, GmpRecord)
    assert record.quotes == []
    assert record.is_absent is True


def test_spread_seed_fixture_loads_with_three_quotes() -> None:
    """data/gmp/hyundai_2024_10.json = the synthetic 3-source spread demo: loads,
    validates, has 3 quotes and a derivable spread (unblocks the 04-06 renderer)."""
    from pipelines import gmp

    record = gmp.load_gmp(KNOWN_DRHP_ID)
    assert isinstance(record, GmpRecord)
    assert len(record.quotes) == 3
    spread = record.spread()
    assert spread is not None
    assert spread.n == 3
    assert spread.high > spread.low  # a genuine disagreement range


def test_precompute_all_isolates_per_ipo_failure(monkeypatch) -> None:
    """precompute-all logs and continues on a per-IPO failure (P14) — one IPO's
    exception never aborts the batch."""
    from pipelines import gmp

    def _flaky(drhp_id, *, write=True):
        if drhp_id == "swiggy_2024_11":
            raise RuntimeError("simulated per-IPO failure")
        return GmpRecord(
            drhp_id=drhp_id, computed_at="t", as_of="t", quotes=[]
        )

    monkeypatch.setattr(gmp, "precompute_gmp", _flaky, raising=True)
    gmp.precompute_all()  # must not raise
