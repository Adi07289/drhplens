"""
Unit tests for agent/nodes/classify.py — the bounded LLM-classify hop (D-05, D-07).

The LLM is STUBBED (patch ``agent.nodes.classify._llm_classify``) — no live Gemini
call ever fires here. The tests assert the DETERMINISTIC envelope around the hop:

  * the allow-list CLAMP drops any tool the model should not be able to dispatch (D-05);
  * ``is_advice_seeking`` / ``is_out_of_scope`` short-circuit to an empty plan so
    compliance-bait and gibberish refuse with no tool thrash (D-07a/c);
  * the classify hop increments ``hops`` by exactly one (P8 budget);
  * an all-models-fail path degrades to an empty plan, never an escaping exception (D-07c).

The classify.md prompt-coverage tests (Task 2) live at the bottom of this file so the
four-category few-shot exemplars cannot silently regress.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest


def _base_state(question: str, hops: int = 0) -> dict:
    """A SupervisorState-shaped dict (GraphState keys + the six supervisor-only keys)."""
    return {
        # --- GraphState (inherited) keys ---
        "question": question,
        "drhp_id": "swiggy_2024_11",
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": True,
        "gate1_max_score": 0.0,
        "sub_questions": [question],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
        # --- SupervisorState-only keys ---
        "hops": hops,
        "tool_calls": 0,
        "tool_plan": [],
        "tool_results": [],
        "started_at": time.monotonic(),
        "is_partial": False,
    }


# ---------------------------------------------------------------------------
# RoutingDecision schema — the Literal tool union is the first D-05 defense
# ---------------------------------------------------------------------------


def test_routing_decision_valid_tool():
    from agent.nodes.classify import RoutingDecision

    d = RoutingDecision(
        tools=["query_forecast"], is_advice_seeking=False, is_out_of_scope=False
    )
    assert d.tools == ["query_forecast"]


def test_routing_decision_rejects_fabricated_tool():
    """The Literal tool union means the model literally cannot name a non-existent tool (D-05)."""
    from pydantic import ValidationError

    from agent.nodes.classify import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(
            tools=["make_me_rich"], is_advice_seeking=False, is_out_of_scope=False
        )


def test_routing_decision_defaults_to_empty_tools():
    from agent.nodes.classify import RoutingDecision

    d = RoutingDecision(is_advice_seeking=False, is_out_of_scope=True)
    assert d.tools == []


def test_routing_decision_has_flag_fields():
    from agent.nodes.classify import RoutingDecision

    assert "is_advice_seeking" in RoutingDecision.model_fields
    assert "is_out_of_scope" in RoutingDecision.model_fields


# ---------------------------------------------------------------------------
# The deterministic allow-list clamp (D-05)
# ---------------------------------------------------------------------------


def test_run_clamps_hallucinated_tool():
    """Even if a non-allow-list name slips past the schema, run() drops it (D-05 clamp).

    ``model_construct`` bypasses the Literal so we can simulate a hallucinated tool
    reaching ``run()`` and prove the deterministic clamp — not the schema — is the
    authority boundary.
    """
    from agent.nodes import classify
    from agent.nodes.classify import RoutingDecision

    fake = RoutingDecision.model_construct(
        tools=["drhp_rag", "delete_database"],
        is_advice_seeking=False,
        is_out_of_scope=False,
    )
    with patch("agent.nodes.classify._llm_classify", return_value=fake):
        result = classify.run(_base_state("What is the issue size?"))

    assert result["tool_plan"] == ["drhp_rag"]
    assert "delete_database" not in result["tool_plan"]


def test_run_passes_through_allowed_tools_in_priority_order():
    from agent.nodes import classify
    from agent.nodes.classify import RoutingDecision

    fake = RoutingDecision(
        tools=["query_forecast", "query_peers"],
        is_advice_seeking=False,
        is_out_of_scope=False,
    )
    with patch("agent.nodes.classify._llm_classify", return_value=fake):
        result = classify.run(
            _base_state("How did comparable IPOs list and what are the peer multiples?")
        )

    assert result["tool_plan"] == ["query_forecast", "query_peers"]


# ---------------------------------------------------------------------------
# Advice / out-of-scope short-circuit (D-07a/c)
# ---------------------------------------------------------------------------


def test_run_advice_seeking_short_circuits():
    """Advice-bait → empty plan, so it refuses downstream with no tool thrash (D-07a)."""
    from agent.nodes import classify
    from agent.nodes.classify import RoutingDecision

    fake = RoutingDecision(
        tools=["drhp_rag", "query_forecast"],
        is_advice_seeking=True,
        is_out_of_scope=False,
    )
    with patch("agent.nodes.classify._llm_classify", return_value=fake):
        result = classify.run(_base_state("Is this IPO worth applying for?", hops=0))

    assert result["tool_plan"] == []
    assert result["hops"] == 1


def test_run_out_of_scope_short_circuits():
    """Gibberish/off-topic/jailbreak/cross-IPO → empty plan (D-07c)."""
    from agent.nodes import classify
    from agent.nodes.classify import RoutingDecision

    fake = RoutingDecision(
        tools=["drhp_rag"], is_advice_seeking=False, is_out_of_scope=True
    )
    with patch("agent.nodes.classify._llm_classify", return_value=fake):
        result = classify.run(_base_state("asdfghjkl qwerty gibberish"))

    assert result["tool_plan"] == []


# ---------------------------------------------------------------------------
# hops increments by exactly one (P8 budget accounting)
# ---------------------------------------------------------------------------


def test_run_increments_hops_by_exactly_one():
    from agent.nodes import classify
    from agent.nodes.classify import RoutingDecision

    fake = RoutingDecision(
        tools=["drhp_rag"], is_advice_seeking=False, is_out_of_scope=False
    )
    with patch("agent.nodes.classify._llm_classify", return_value=fake):
        result = classify.run(_base_state("What is the issue size?", hops=2))

    assert result["hops"] == 3
    assert result["tool_plan"] == ["drhp_rag"]


# ---------------------------------------------------------------------------
# Graceful degrade when every retry + model fails (D-07c, never a crash)
# ---------------------------------------------------------------------------


def test_run_all_models_fail_returns_empty_plan():
    """If every retry + model fails, run() degrades to an empty plan — never raises (D-07c)."""
    from agent.nodes import classify

    with patch(
        "agent.nodes.classify._llm_classify", side_effect=RuntimeError("503 on every model")
    ):
        state = _base_state("What is the issue size?", hops=0)
        result = classify.run(state)  # must NOT raise

    assert result["tool_plan"] == []
    assert result["hops"] == 1


def test_run_preserves_inherited_state_keys():
    """run() overwrites only tool_plan + hops; every inherited key is threaded through."""
    from agent.nodes import classify
    from agent.nodes.classify import RoutingDecision

    fake = RoutingDecision(
        tools=["drhp_rag"], is_advice_seeking=False, is_out_of_scope=False
    )
    state = _base_state("What is the issue size?")
    with patch("agent.nodes.classify._llm_classify", return_value=fake):
        result = classify.run(state)

    assert result["drhp_id"] == "swiggy_2024_11"
    assert result["question"] == "What is the issue size?"
    assert result["tool_calls"] == 0


# ---------------------------------------------------------------------------
# classify.md prompt coverage (Task 2)
#
# The four-category few-shot exemplars are what make routing stable and
# jailbreak-aware. These tests pin the exemplar coverage so it cannot silently
# regress, and assert the classifier framing carries ZERO banned prescriptive
# tokens (it is a classifier, not an answer).
# ---------------------------------------------------------------------------


def _load_classify_prompt() -> str:
    from agent.nodes.classify import _load_prompt

    _load_prompt.cache_clear()  # ignore any cache primed by another test
    return _load_prompt()


def test_prompt_loads_non_empty():
    text = _load_classify_prompt()
    assert text.strip(), "classify.md must load and be non-empty"


def test_prompt_covers_four_d07_categories():
    """All four D-07 weird-query categories must be cued so routing cannot silently regress."""
    text = _load_classify_prompt().lower()
    # (a) advice-seeking / compliance-bait
    assert "advice" in text, "missing the advice-seeking category cue"
    # (b) jailbreak / prompt-injection
    assert "ignore" in text and "system prompt" in text, "missing the jailbreak category cue"
    # (c) off-topic / gibberish
    assert "off-topic" in text or "gibberish" in text, "missing the off-topic/gibberish cue"
    # (d) cross-IPO / compare
    assert (
        "compare" in text or "cross-ipo" in text or "another ipo" in text
    ), "missing the cross-IPO/compare cue"


def test_prompt_names_all_four_tools():
    """The prompt must enumerate exactly the four allow-listed tools (D-05 framing)."""
    text = _load_classify_prompt()
    for tool in ("drhp_rag", "query_peers", "query_forecast", "query_redflags"):
        assert tool in text, f"classify.md must name the {tool} tool"


def test_prompt_has_no_banned_prescriptive_token():
    """classify.md is a classifier framing, not an answer — it must carry zero banned tokens."""
    from compliance.scrubber import scrub

    result = scrub(_load_classify_prompt())
    assert result.passed, f"classify.md contains a banned prescriptive token: {result.match!r}"
