"""
Unit tests — the three read-only tool loader nodes (D-01) + the GMP fold (D-04).

Every assertion runs OFFLINE against the committed fixtures — no LLM, no Qdrant,
no network. `swiggy_2024_11` is the only IPO with all four records (forecast +
peers + red-flags + a GMP file, though its GMP is the absent state); `hyundai_2024_10`
has a forecast + a POPULATED GMP but NO peers/red-flag file (the natural
missing-record case). Both are catalogue-known ids.

Pins the D-01/D-04 contract:
  - each node returns a provenance-tagged record, increments tool_calls by exactly
    1, and pops ONLY itself from tool_plan;
  - a missing record -> abstain=True, record=None with no exception (P14);
  - query_forecast surfaces the caveated gmp_gap when a GMP is reported and OMITS
    it when absent (D-04), and never leaks a GMP value into a model field;
  - an unknown / traversal drhp_id is rejected by the allow-list before any read.
"""
from __future__ import annotations

import json

import pytest

from agent.tools import query_forecast, query_peers, query_redflags
from ui.copy import GMP_CAVEAT

SWIGGY = "swiggy_2024_11"      # all four records; GMP is the ABSENT state (quotes == [])
HYUNDAI = "hyundai_2024_10"    # forecast + POPULATED GMP; NO peers/red-flag file


def _state(drhp_id: str, plan: list[str]) -> dict:
    """A minimal SupervisorState the tool nodes read/write."""
    return {
        "question": "q",
        "drhp_id": drhp_id,
        "regenerate_attempts": 0,
        "hops": 0,
        "tool_calls": 0,
        "tool_plan": list(plan),
        "tool_results": [],
        "started_at": 0.0,
        "is_partial": False,
    }


# ---------------------------------------------------------------------------
# Each node: record + provenance + tool_calls++ + pops only itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module, tool_name, provenance_dir",
    [
        (query_peers, "query_peers", "peers"),
        (query_forecast, "query_forecast", "forecasts"),
        (query_redflags, "query_redflags", "redflag"),
    ],
)
def test_node_loads_record_and_advances_state(module, tool_name, provenance_dir):
    # plan carries this tool plus a sibling that must NOT be popped.
    state = _state(SWIGGY, [tool_name, "other_tool"])

    out = module.run(state)

    # exactly one provenance-tagged result for this tool, with a real record.
    assert len(out["tool_results"]) == 1
    entry = out["tool_results"][0]
    assert entry["tool"] == tool_name
    assert entry["record"] is not None
    assert entry["provenance"] == f"data/{provenance_dir}/{SWIGGY}.json"
    assert entry["abstain"] is False

    # tool_calls incremented by EXACTLY 1.
    assert out["tool_calls"] == 1

    # ONLY this tool popped from tool_plan; the sibling survives.
    assert tool_name not in out["tool_plan"]
    assert out["tool_plan"] == ["other_tool"]


@pytest.mark.parametrize(
    "module, tool_name",
    [(query_peers, "query_peers"), (query_forecast, "query_forecast"),
     (query_redflags, "query_redflags")],
)
def test_node_appends_not_overwrites_prior_results(module, tool_name):
    state = _state(SWIGGY, [tool_name])
    state["tool_results"] = [{"tool": "prior", "record": None, "provenance": None,
                              "abstain": True}]
    state["tool_calls"] = 2

    out = module.run(state)

    # prior result preserved; new one appended; counter continued.
    assert len(out["tool_results"]) == 2
    assert out["tool_results"][0]["tool"] == "prior"
    assert out["tool_results"][1]["tool"] == tool_name
    assert out["tool_calls"] == 3


# ---------------------------------------------------------------------------
# Missing record -> honest abstain (P14), no exception
# ---------------------------------------------------------------------------


def test_missing_record_abstains_via_monkeypatched_empty_dir(monkeypatch, tmp_path):
    """A known drhp_id whose file does not exist -> abstain=True, record=None."""
    import pipelines.peers as peers_mod

    # Point the loader at an EMPTY dir so swiggy (a known id) has no file.
    monkeypatch.setattr(peers_mod, "PEERS_DIR", tmp_path)

    out = query_peers.run(_state(SWIGGY, ["query_peers"]))

    entry = out["tool_results"][0]
    assert entry["abstain"] is True
    assert entry["record"] is None
    assert entry["provenance"] is None
    # tool_calls still advanced; the honest abstain is first-class, not an error.
    assert out["tool_calls"] == 1
    assert out["tool_plan"] == []


def test_missing_record_natural_case_no_exception():
    """hyundai has NO peers/red-flag file (real fixture reality) -> honest abstain."""
    for module in (query_peers, query_redflags):
        out = module.run(_state(HYUNDAI, [module.TOOL_NAME]))
        entry = out["tool_results"][0]
        assert entry["abstain"] is True
        assert entry["record"] is None


# ---------------------------------------------------------------------------
# GMP fold (D-04): present -> caveated gmp_gap; absent -> omitted; never a model field
# ---------------------------------------------------------------------------


def test_query_forecast_surfaces_gmp_gap_when_reported():
    # hyundai has a POPULATED GMP record (3 quotes).
    out = query_forecast.run(_state(HYUNDAI, ["query_forecast"]))
    entry = out["tool_results"][0]

    assert "gmp_gap" in entry
    gap = entry["gmp_gap"]
    # the GMP quotes are surfaced verbatim (display-only)...
    assert len(gap["gmp_quotes"]) == 3
    assert gap["gmp_spread"]["n"] == 3
    # ...with the mandatory display-only caveat (single-source copy).
    assert gap["caveat"] == GMP_CAVEAT
    assert "never use it in any forecast" in gap["caveat"]


def test_query_forecast_omits_gmp_gap_when_absent():
    # swiggy's GMP record is the ABSENT state (quotes == []).
    out = query_forecast.run(_state(SWIGGY, ["query_forecast"]))
    entry = out["tool_results"][0]

    assert "gmp_gap" not in entry           # fold omitted, no fabricated gap (D-04)
    assert entry["record"] is not None      # the forecast band itself is present


def test_gmp_value_never_flows_into_a_model_field():
    """GMP figures appear ONLY under gmp_gap, never inside the forecast record (P4)."""
    out = query_forecast.run(_state(HYUNDAI, ["query_forecast"]))
    entry = out["tool_results"][0]

    # the forecast record is GMP-free — no gmp key and none of the GMP values.
    record_blob = json.dumps(entry["record"])
    assert "gmp" not in record_blob.lower()
    gmp_values = {q["value"] for q in entry["gmp_gap"]["gmp_quotes"]}
    assert gmp_values == {25.0, 67.0, 50.0}
    for v in gmp_values:
        # the GMP premium (₹/share) is not present anywhere in the % model band.
        assert str(v) not in json.dumps(entry["record"].get("interval"))


# ---------------------------------------------------------------------------
# Unknown / traversal drhp_id -> rejected by the allow-list before any read
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module", [query_peers, query_forecast, query_redflags]
)
def test_unknown_drhp_id_rejected_before_read(module):
    for hostile in ("../../etc/passwd", "not_a_real_ipo", "swiggy_2024_11/../x"):
        with pytest.raises(ValueError):
            module.run(_state(hostile, [module.TOOL_NAME]))
