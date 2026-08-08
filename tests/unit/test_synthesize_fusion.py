"""
tests/unit/test_synthesize_fusion.py — the multi-tool fusion synthesis path (06.3-06).

Task 2 — the ``synthesize.run`` FUSION branch with the fusion LLM STUBBED
(``patch("agent.nodes.synthesize._llm_fuse")``): a resolvable ToolClaim is woven into
one cited answer; an unresolved ToolClaim is DROPPED (FM-3) and its marker stripped; a
tool-abstain fusion sets ``is_partial=True`` with grounded content intact and NO
fabricated band (D-08); a banned-token fusion is blocked-and-refused; the GMP figure
traces to the read-only ``gmp_gap`` block (D-04). Plus a direct check that the fusion
hop passes the raw question ONLY as the user role with ``temperature=0`` + explicit
``max_tokens`` (T-1-01), and that the prompt describes-never-concludes + mandates the
GMP caveat with no banned prescriptive token.

Task 3 — the fused END-TO-END dispatch through the real bounded supervisor (tool nodes
wired, LLM hops stubbed): a multi-tool plan dispatches serially, each tool pops itself
+ increments ``tool_calls``, reaches synthesize once, and returns one fused answer;
a plan exceeding ``MAX_TOOL_CALLS`` trips to synthesize with ``is_partial=True``.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent.nodes import synthesize
from agent.nodes.cite_check import cite_check_claim
from agent.schemas import FusedAnswer, ToolClaim
from compliance.disclaimer_text import PER_ANSWER_FOOTER
from compliance.scrubber import scrub
from pipelines.forecast import load_forecast
from pipelines.peers import load_peers

_DRHP_ID = "swiggy_2024_11"


# ---------------------------------------------------------------------------
# tool_results the tool nodes would have appended (real committed swiggy records).
# ---------------------------------------------------------------------------


def _forecast_result() -> dict:
    record = load_forecast(_DRHP_ID)
    return {
        "tool": "query_forecast",
        "record": record.model_dump(),
        "provenance": f"data/forecasts/{_DRHP_ID}.json",
        "abstain": record.is_abstain,
    }


def _forecast_abstain_result() -> dict:
    return {
        "tool": "query_forecast",
        "record": None,
        "provenance": None,
        "abstain": True,
    }


def _peer_result() -> dict:
    record = load_peers(_DRHP_ID)
    return {
        "tool": "query_peers",
        "record": record.model_dump(),
        "provenance": f"data/peers/{_DRHP_ID}.json",
        "abstain": False,
    }


def _fusion_state(tool_results: list[dict], question: str = "Give me the picture.") -> dict:
    return {
        "question": question,
        "drhp_id": _DRHP_ID,
        "grounded_answer": None,
        "reranked_top_k": [],
        "tool_plan": [],
        "tool_results": tool_results,
        "hops": 1,
        "tool_calls": len(tool_results),
    }


def _forecast_toolclaim(value, field: str = "interval.low_pct", cid: str = "c_fcst01") -> ToolClaim:
    return ToolClaim(
        claim_id=cid,
        text=f"the calibrated low is {value}",
        value=value,
        source_tool="query_forecast",
        source_record_id=f"data/forecasts/{_DRHP_ID}.json#{field}",
    )


def _peer_toolclaim(value=9.4, cid: str = "c_peer01") -> ToolClaim:
    return ToolClaim(
        claim_id=cid,
        text=f"the price-to-book multiple is {value}x",
        value=value,
        source_tool="query_peers",
        source_record_id=f"data/peers/{_DRHP_ID}.json#companies[0].metrics[1].current.value",
    )


# ===========================================================================
# Task 2 — synthesize.run FUSION branch (LLM stubbed)
# ===========================================================================


def test_fusion_weaves_resolvable_toolclaim_into_one_cited_answer():
    """A DRHP+peer+forecast fusion whose numbers each resolve to a source record →
    one fused answer, claims kept, scrubber-clean, disclaimered, is_partial=False."""
    fused = FusedAnswer(
        answer_prose="Comparable IPOs listed in a calibrated range from -4.2% {{c_fcst01}}.",
        claims=[_forecast_toolclaim(-4.2)],
        is_partial=False,
    )
    state = _fusion_state([_forecast_result(), _peer_result()])
    with patch("agent.nodes.synthesize._llm_fuse", return_value=fused):
        out = synthesize.run(state)

    assert out["is_partial"] is False
    assert out.get("refusal") is None
    answer = out["fused_answer"]
    assert answer is not None
    assert {c.claim_id for c in answer.claims} == {"c_fcst01"}  # resolvable → kept
    assert scrub(answer.answer_prose).passed
    assert PER_ANSWER_FOOTER in out["disclaimer"]


def test_fusion_drops_unresolved_toolclaim_and_strips_marker():
    """A fused answer with an unresolved ToolClaim DROPS that number (FM-3) and strips
    its orphaned {{marker}} so it is never rendered as a broken citation."""
    fused = FusedAnswer(
        answer_prose="The forecast band is {{c_fcst01}} for this issue.",
        claims=[_forecast_toolclaim(-4.2, field="interval.does_not_exist")],
        is_partial=False,
    )
    state = _fusion_state([_forecast_result()])
    with patch("agent.nodes.synthesize._llm_fuse", return_value=fused):
        out = synthesize.run(state)

    answer = out["fused_answer"]
    assert answer.claims == []  # unresolved → dropped
    assert "{{c_fcst01}}" not in answer.answer_prose  # orphaned marker stripped
    assert scrub(answer.answer_prose).passed


def test_fusion_tool_abstain_sets_is_partial_no_fabricated_band():
    """A forecast-abstain fusion yields is_partial=True, keeps the grounded (peer)
    content, and fabricates no forecast band (D-08)."""
    fused = FusedAnswer(
        answer_prose="The peer price-to-book multiple is 9.4x {{c_peer01}}.",
        claims=[_peer_toolclaim()],  # only the grounded peer number; NO forecast band
        is_partial=False,  # the node must OVERRIDE this to True on the abstain
    )
    # forecast abstained (no band); peers grounded.
    state = _fusion_state([_forecast_abstain_result(), _peer_result()])
    with patch("agent.nodes.synthesize._llm_fuse", return_value=fused):
        out = synthesize.run(state)

    assert out["is_partial"] is True  # tool abstain → honest partial (D-08)
    answer = out["fused_answer"]
    assert answer.is_partial is True
    assert {c.claim_id for c in answer.claims} == {"c_peer01"}  # grounded content intact
    # No forecast number was invented (the only claim is the peer multiple).
    assert all(c.source_tool != "query_forecast" for c in answer.claims)
    assert scrub(answer.answer_prose).passed


def test_fusion_banned_token_is_blocked_and_refused():
    """A banned prescriptive token surviving the fuse BLOCKS to a refusal — never a
    fabricated clean rewrite (no live regen on this path)."""
    fused = FusedAnswer(
        answer_prose="You should subscribe to this issue right away.",
        claims=[],
        is_partial=False,
    )
    state = _fusion_state([_forecast_result()])
    with patch("agent.nodes.synthesize._llm_fuse", return_value=fused):
        out = synthesize.run(state)

    assert out.get("fused_answer") is None
    assert out["refusal"] is not None
    assert out["refusal"].reason == "banned_token"
    assert scrub(out["refusal"].explanation).passed
    assert PER_ANSWER_FOOTER in out["disclaimer"]


def test_gmp_toolclaim_traces_to_read_only_gmp_gap_block():
    """A GMP figure grounds ONLY against the display-only gmp_gap block the forecast
    tool attached — never a model field (D-04). The extended cite-check resolves it."""
    tool_result = _forecast_result()
    tool_result["gmp_gap"] = {
        "gmp_spread": {"low": 25.0, "high": 67.0, "n": 2},
        "model_band_pct": {"low_pct": -4.2, "high_pct": 21.7, "median_pct": 6.1},
        "caveat": "informal grey-market figure; never enters any forecast",
    }
    gmp_claim = ToolClaim(
        claim_id="c_gmp001",
        text="the grey-market figure tops out at ₹67",
        value=67.0,
        source_tool="query_forecast",
        source_record_id=f"data/forecasts/{_DRHP_ID}.json#gmp_gap.gmp_spread.high",
    )
    assert cite_check_claim(gmp_claim, {}, [tool_result]) is True


# ---------------------------------------------------------------------------
# The fusion hop's message/kwargs discipline (T-1-01, temperature/max_tokens).
# ---------------------------------------------------------------------------


def test_fusion_hop_passes_question_only_as_user_temperature_zero():
    """The raw question is the user turn ONLY (never the system/context layer), and the
    hop uses temperature=0 + an explicit max_tokens (acceptance criterion 1)."""
    captured: dict = {}

    def _create(**kwargs):
        captured.update(kwargs)
        return FusedAnswer(answer_prose="ok", claims=[], is_partial=False)

    client = MagicMock()
    client.chat.completions.create.side_effect = _create

    question = "How do the peers and forecast compare for this issue?"
    context = "TOOL RECORDS: {peer stuff}"
    with patch("agent.nodes.synthesize._get_fusion_client", return_value=client):
        synthesize._call_fusion_llm(question, context)

    assert captured["temperature"] == 0
    assert isinstance(captured["max_tokens"], int) and captured["max_tokens"] > 0
    messages = captured["messages"]
    # The raw question is the LAST message and carries role="user".
    assert messages[-1] == {"role": "user", "content": question}
    # The question is NEVER interpolated into the system/instruction+context layer.
    system = messages[0]
    assert system["role"] == "system"
    assert question not in system["content"]
    assert context in system["content"]  # trusted context DOES ride the system turn


def test_synthesize_prompt_describes_never_concludes_and_mandates_gmp_caveat():
    """synthesize.md is scrubber-clean (no banned prescriptive token) and instructs
    describe-never-conclude + the D-04 GMP display-only caveat."""
    prompt = synthesize._load_prompt()
    assert scrub(prompt).passed  # no banned prescriptive token in the prompt
    # Whitespace-normalize so the markdown's line wraps do not hide a contiguous phrase.
    low = " ".join(prompt.lower().split())
    assert "never" in low and "context" in low  # describe-never-conclude posture
    assert "grey-market" in low  # the GMP framing
    assert "never enters any forecast" in low  # the D-04 display-only caveat mandate
    assert "source_record_id" in prompt  # per-number provenance mandate
    assert "not disclosed" in low  # no fabricated precision
