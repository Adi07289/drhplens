"""
tests/unit/test_cite_check_toolclaim.py — the type-dispatched cite-check (06.3-06, D-03).

The extended cite-check DISPATCHES on claim type without forking the existing algorithm:

  * A ``Claim`` runs the EXISTING DRHP-span + ``CITE_CHECK_TOKEN_RATIO`` fuzzy path,
    byte-for-byte unchanged (regression-guarded here against the original ``cite_check``).
  * A ``ToolClaim`` resolves its ``source_record_id`` back to the committed record the
    tool already loaded into ``tool_results`` and reconciles ``value`` against that
    record's number using the ALREADY-IMPLEMENTED ``NUMERIC_GROUNDING_REL_TOLERANCE``
    (0.01) + lakh/crore/million unit normalization. A ToolClaim whose number cannot be
    resolved to its source record FAILS the check and is DROPPED (FM-3) — never rendered,
    never fabricated.

These tests use the REAL committed swiggy records (``data/{forecasts,peers}/*.json``)
plus a couple of synthetic ``tool_results`` for the unit-normalization / not-disclosed
paths — the cite-check reconciles against the in-memory ``tool_results`` the tool nodes
appended, so no file re-read (and no path-safety concern) is introduced here.
"""
from __future__ import annotations

from agent.nodes.cite_check import (
    cite_check,
    cite_check_claim,
    partition_fused_claims,
)
from agent.schemas import Claim, GroundedAnswer, RetrievedChunkRef, ToolClaim
from pipelines.forecast import load_forecast
from pipelines.peers import load_peers

_DRHP_ID = "swiggy_2024_11"


# ---------------------------------------------------------------------------
# Helpers — build the tool_results the tool nodes would have appended.
# ---------------------------------------------------------------------------


def _forecast_results() -> list[dict]:
    record = load_forecast(_DRHP_ID)
    return [
        {
            "tool": "query_forecast",
            "record": record.model_dump(),
            "provenance": f"data/forecasts/{_DRHP_ID}.json",
            "abstain": record.is_abstain,
        }
    ]


def _peer_results() -> list[dict]:
    record = load_peers(_DRHP_ID)
    return [
        {
            "tool": "query_peers",
            "record": record.model_dump(),
            "provenance": f"data/peers/{_DRHP_ID}.json",
            "abstain": False,
        }
    ]


def _tool_claim(value, source_tool: str, field_ref: str, claim_id: str = "c_tool01") -> ToolClaim:
    provenance = {
        "query_forecast": f"data/forecasts/{_DRHP_ID}.json",
        "query_peers": f"data/peers/{_DRHP_ID}.json",
        "query_redflags": f"data/redflag/{_DRHP_ID}.json",
    }[source_tool]
    return ToolClaim(
        claim_id=claim_id,
        text=f"the value is {value}",
        value=value,
        source_tool=source_tool,  # type: ignore[arg-type]
        source_record_id=f"{provenance}#{field_ref}",
    )


def _drhp_claim(text: str, span: str, claim_id: str = "c_drhp01") -> tuple[Claim, dict]:
    """A DRHP-grounded Claim + the retrieved_chunks that support it."""
    source = RetrievedChunkRef(
        chunk_id="chunk_x",
        page_start=42,
        page_end=42,
        section="The Offer",
        verbatim_span=span,
        span_offsets=[0, len(span)],
    )
    claim = Claim(
        claim_id=claim_id,
        text=text,
        source_chunk_id="chunk_x",
        drhp_page=42,
        section="The Offer",
        verbatim_span=span,
        span_offsets=[0, len(span)],
        sources=[source],
    )
    return claim, {"chunk_x": span}


# ---------------------------------------------------------------------------
# ToolClaim numeric reconcile — the D-03 provenance path.
# ---------------------------------------------------------------------------


def test_toolclaim_value_within_tolerance_is_grounded():
    """A ToolClaim whose value matches its committed source-record field within
    NUMERIC_GROUNDING_REL_TOLERANCE is grounded (kept)."""
    # swiggy forecast interval.low_pct == -4.2, median_pct == 6.1
    claim = _tool_claim(-4.2, "query_forecast", "interval.low_pct")
    assert cite_check_claim(claim, {}, _forecast_results()) is True

    claim2 = _tool_claim(6.1, "query_forecast", "interval.median_pct")
    assert cite_check_claim(claim2, {}, _forecast_results()) is True


def test_toolclaim_off_by_more_than_tolerance_is_dropped():
    """A ToolClaim whose value drifts past the tolerance from its source record is
    DROPPED — never rendered (FM-3)."""
    # width_pts == 25.9; claim 30.0 is ~16% off, far past the 1% tolerance.
    claim = _tool_claim(30.0, "query_forecast", "interval.width_pts")
    assert cite_check_claim(claim, {}, _forecast_results()) is False


def test_toolclaim_peer_multiple_within_tolerance_grounded():
    """A peer multiple ToolClaim reconciles against the committed peer cell value."""
    # companies[0] (Swiggy) metrics[1] == pb, current.value == 9.4
    claim = _tool_claim(9.4, "query_peers", "companies[0].metrics[1].current.value")
    assert cite_check_claim(claim, {}, _peer_results()) is True


def test_toolclaim_against_null_source_cell_is_dropped():
    """A numeric ToolClaim pointing at a null/NM source cell cannot ground → dropped."""
    # companies[0] metrics[0] == pe, current.value == null (not_meaningful)
    claim = _tool_claim(18.0, "query_peers", "companies[0].metrics[0].current.value")
    assert cite_check_claim(claim, {}, _peer_results()) is False


def test_toolclaim_lakh_crore_reconciles_after_normalization():
    """'₹11,247 crore' reconciles with a lakh-denominated source record after the
    existing lakh/crore unit normalization."""
    tool_results = [
        {
            "tool": "query_peers",
            "record": {"issue_size_text": "₹11,24,700 lakh"},  # == 11,247 crore
            "provenance": f"data/peers/{_DRHP_ID}.json",
            "abstain": False,
        }
    ]
    claim = _tool_claim("₹11,247 crore", "query_peers", "issue_size_text")
    assert cite_check_claim(claim, {}, tool_results) is True


def test_toolclaim_unresolvable_source_record_id_is_dropped():
    """A ToolClaim whose source_record_id resolves to no field is DROPPED (FM-3)."""
    # nonexistent field on a real record → unresolvable.
    claim = _tool_claim(9.4, "query_peers", "companies[99].metrics[0].current.value")
    assert cite_check_claim(claim, {}, _peer_results()) is False

    # a provenance that matches no tool_results entry at all → unresolvable.
    orphan = _tool_claim(6.1, "query_forecast", "interval.median_pct")
    assert cite_check_claim(orphan, {}, _peer_results()) is False


def test_toolclaim_non_numeric_value_resolving_field_is_grounded():
    """An honest non-numeric ToolClaim value ('not disclosed') grounds when its source
    field resolves to a concrete value — never a fabricated number (numeric-faithfulness)."""
    tool_results = [
        {
            "tool": "query_redflags",
            "record": {"promoter_pledge_pct": "not disclosed"},
            "provenance": f"data/redflag/{_DRHP_ID}.json",
            "abstain": False,
        }
    ]
    claim = _tool_claim("not disclosed", "query_redflags", "promoter_pledge_pct")
    assert cite_check_claim(claim, {}, tool_results) is True


# ---------------------------------------------------------------------------
# DRHP Claim path — MUST stay byte-identical to the original cite_check (no regression).
# ---------------------------------------------------------------------------


def test_drhp_claim_grounds_identically_to_original_cite_check():
    """A DRHP Claim dispatches to the EXISTING span path; the new dispatcher's verdict
    equals the original cite_check verdict (regression guard, Claim path unchanged)."""
    claim, chunks = _drhp_claim(
        "The issue size is ₹11,300 crore",
        "The total issue size is ₹11,300 crore comprising fresh issue and OFS.",
    )
    ok_old, _ = cite_check(
        GroundedAnswer(answer_prose=f"x {{{{{claim.claim_id}}}}}", claims=[claim]),
        chunks,
    )
    ok_new = cite_check_claim(claim, chunks, [])
    assert ok_new is ok_old is True


def test_drhp_claim_ungrounded_refuses_identically():
    """A DRHP Claim whose number is absent from its chunk fails identically (no repair,
    no fabrication) — the Claim path is unchanged."""
    claim, chunks = _drhp_claim(
        "The issue size is ₹99,999 crore",  # a number NOT in the span
        "The total issue size is ₹11,300 crore comprising fresh issue and OFS.",
    )
    ok_old, _ = cite_check(
        GroundedAnswer(answer_prose=f"x {{{{{claim.claim_id}}}}}", claims=[claim]),
        chunks,
    )
    ok_new = cite_check_claim(claim, chunks, [])
    assert ok_new is ok_old is False


# ---------------------------------------------------------------------------
# partition_fused_claims — the per-claim keep/drop synthesize consumes.
# ---------------------------------------------------------------------------


def test_partition_fused_claims_keeps_grounded_drops_unresolved():
    """A mixed union: a grounded ToolClaim + a grounded DRHP Claim are kept; an
    unresolvable ToolClaim is dropped (its id reported so synthesize can strip it)."""
    grounded_tool = _tool_claim(
        -4.2, "query_forecast", "interval.low_pct", claim_id="c_keep01"
    )
    unresolved_tool = _tool_claim(
        30.0, "query_forecast", "interval.width_pts", claim_id="c_drop01"
    )
    drhp_claim, chunks = _drhp_claim(
        "The issue size is ₹11,300 crore",
        "The total issue size is ₹11,300 crore comprising fresh issue and OFS.",
        claim_id="c_keep02",
    )

    kept, dropped = partition_fused_claims(
        [grounded_tool, unresolved_tool, drhp_claim], chunks, _forecast_results()
    )

    kept_ids = {c.claim_id for c in kept}
    assert kept_ids == {"c_keep01", "c_keep02"}
    assert dropped == ["c_drop01"]
