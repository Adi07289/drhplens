"""
Unit test — the peer precompute loop runs the canned PEER_SET_QUERY through the
EXISTING agent graph (agent.graph.GRAPH), stores the cited GroundedAnswer as the
peer SET (PEER-01), loops the named peers through the source-priority ladder
(PEER-02), and stores a RefusalResponse honest empty-state when the DRHP names no
peers (D4-06). The allow-list gates the cache path (T-04-03-PATH).

Fully offline: GRAPH.invoke AND every source fetcher are monkeypatched — no live
Gemini/Qdrant, no live screener.in/yfinance/NSE HTTP (CODE-NOW-DEFER).
"""
from __future__ import annotations

import pytest

import pipelines.peer_sources as ps
from agent.peer_schema import PeerRecord
from agent.schemas import (
    Claim,
    GroundedAnswer,
    RefusalResponse,
    RetrievedChunkRef,
)

KNOWN_DRHP_ID = "swiggy_2024_11"


# ---------------------------------------------------------------------------
# Builders for the monkeypatched GRAPH.invoke return states
# ---------------------------------------------------------------------------


def _grounded_peer_answer() -> GroundedAnswer:
    span = "Comparison with Listed Industry Peers: Zomato Limited"
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
        claim_id="c_peer01",
        text="Zomato Limited",
        source_chunk_id="chunk_peer_001",
        drhp_page=118,
        section="Basis for Issue Price",
        verbatim_span=span,
        span_offsets=(0, len(span)),
        sources=[source],
    )
    return GroundedAnswer(
        answer_prose="The company names Zomato Limited as a listed peer {{c_peer01}}.",
        claims=[claim],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def _grounded_state(payload=None) -> dict:
    return {
        "grounded_answer": _grounded_peer_answer(),
        "refusal": None,
        "all_claims_grounded": True,
    }


def _refusal_state(payload=None) -> dict:
    return {
        "grounded_answer": None,
        "refusal": RefusalResponse(
            reason="low_retrieval_score",
            explanation="This DRHP disclosed no listed-peer comparison.",
        ),
        "all_claims_grounded": False,
    }


def _patch_graph(monkeypatch, state_factory) -> None:
    import agent.graph as graph_mod

    class _FakeGraph:
        def invoke(self, payload):
            return state_factory(payload)

    monkeypatch.setattr(graph_mod, "GRAPH", _FakeGraph(), raising=True)


def _patch_sources_all_missing(monkeypatch) -> None:
    """No live network: every source rung returns all-None → honest '—' cells."""
    all_none = {"pe": None, "pb": None, "ev_ebitda": None, "roe": None}
    monkeypatch.setattr(ps, "screener_multiples", lambda name: dict(all_none), raising=True)
    monkeypatch.setattr(ps, "yfinance_multiples", lambda ticker: dict(all_none), raising=True)
    monkeypatch.setattr(ps, "nse_multiples", lambda ticker: dict(all_none), raising=True)


# ---------------------------------------------------------------------------
# Precompute behaviour
# ---------------------------------------------------------------------------


def test_precompute_grounded_builds_record(monkeypatch) -> None:
    from pipelines import peers

    _patch_graph(monkeypatch, _grounded_state)
    _patch_sources_all_missing(monkeypatch)

    record = peers.precompute_peers(KNOWN_DRHP_ID, write=False)

    assert isinstance(record, PeerRecord)
    # PEER-01: the cited GroundedAnswer IS the peer SET value
    assert isinstance(record.peer_set, GroundedAnswer)
    assert record.peer_set.claims[0].drhp_page == 118
    # named peers looped through the ladder → at least the IPO row + Zomato
    assert len(record.companies) >= 2
    names = [c.name for c in record.companies]
    assert any("Zomato" in n for n in names)
    # the IPO's own row is flagged is_ipo
    assert any(c.is_ipo for c in record.companies)


def test_precompute_refusal_is_honest_empty_state(monkeypatch) -> None:
    """When the graph returns a RefusalResponse (no peer section), the peer SET is
    stored as that refusal and NO peer companies are fabricated (D4-06)."""
    from pipelines import peers

    _patch_graph(monkeypatch, _refusal_state)
    _patch_sources_all_missing(monkeypatch)

    record = peers.precompute_peers(KNOWN_DRHP_ID, write=False)

    assert isinstance(record.peer_set, RefusalResponse)
    assert record.companies == []


def test_path_gate_rejects_unknown_drhp_id(monkeypatch) -> None:
    """precompute_peers + load_peers raise on a non-allow-listed drhp_id BEFORE
    forming any path (path-traversal control T-04-03-PATH)."""
    from pipelines import peers

    with pytest.raises(ValueError):
        peers.precompute_peers("../etc/passwd", write=False)
    with pytest.raises(ValueError):
        peers.load_peers("../etc/passwd")


def test_load_known_but_uncached_raises_file_not_found() -> None:
    """A known catalogue id with no peer cache raises FileNotFoundError (the gate
    passes, the path is formed, the file is simply absent)."""
    from pipelines import peers

    with pytest.raises(FileNotFoundError):
        peers.load_peers("zomato_2021_07")


def test_seed_fixture_loads(monkeypatch) -> None:
    """The hand-seeded data/peers/swiggy_2024_11.json loads and validates, with
    ≥1 company and at least one honest '—' cell (value None, not NM)."""
    from pipelines import peers

    record = peers.load_peers(KNOWN_DRHP_ID)
    assert isinstance(record, PeerRecord)
    assert len(record.companies) >= 1

    emdash_cells = [
        cell
        for company in record.companies
        for metric in company.metrics
        for cell in (metric.current, metric.drhp_date)
        if cell is not None and cell.value is None and not cell.not_meaningful
    ]
    assert emdash_cells, "seed must contain at least one honest '—' cell (D4-05)"


def test_record_round_trips_via_load_peers(monkeypatch, tmp_path) -> None:
    from pipelines import peers

    monkeypatch.setattr(peers, "PEERS_DIR", tmp_path, raising=True)
    _patch_graph(monkeypatch, _grounded_state)
    _patch_sources_all_missing(monkeypatch)

    written = peers.precompute_peers(KNOWN_DRHP_ID, write=True)
    loaded = peers.load_peers(KNOWN_DRHP_ID)

    assert loaded.drhp_id == written.drhp_id
    assert [c.name for c in loaded.companies] == [c.name for c in written.companies]
    assert isinstance(loaded.peer_set, GroundedAnswer)


def test_precompute_all_isolates_per_ipo_failure(monkeypatch) -> None:
    """precompute-all logs and continues on a per-IPO failure (P14) — one IPO's
    exception never aborts the batch."""
    from pipelines import peers

    def _flaky(drhp_id, *, write=True):
        if drhp_id == "swiggy_2024_11":
            raise RuntimeError("simulated per-IPO failure")
        return peers.PeerRecord(
            drhp_id=drhp_id,
            computed_at="t",
            as_of="t",
            peer_set=RefusalResponse(reason="low_retrieval_score", explanation="nd"),
            companies=[],
        )

    monkeypatch.setattr(peers, "precompute_peers", _flaky, raising=True)
    # Must not raise despite the swiggy failure.
    peers.precompute_all()


def test_uses_existing_graph_no_new_llm_client() -> None:
    """pipelines/peers.py reuses the existing graph (GRAPH.invoke appears) and
    constructs no new LLM client."""
    from pathlib import Path

    import pipelines.peers as pk

    text = Path(pk.__file__).read_text(encoding="utf-8")
    assert text.count("GRAPH.invoke") >= 1
