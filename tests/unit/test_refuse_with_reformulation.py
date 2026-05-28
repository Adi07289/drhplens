"""
Unit tests for agent/nodes/refuse_with_reformulation.py — shared terminal refusal node.

All external calls (embed_query, search_relaxed) are mocked.
Verifies: RESEARCH Open Question 5 algorithm, D-04 reformulation, T-1-01.
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

from agent.policies import DRHP_ID_DEFAULT, RELAXED_SEARCH_TOP_SECTIONS
from agent.schemas import RefusalResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hits(sections: list[str]) -> list[dict]:
    """Make fake Qdrant hits with given section names."""
    return [
        {
            "id": f"chunk_{i:03d}",
            "score": 0.9 - i * 0.01,
            "payload": {
                "chunk_id": f"chunk_{i:03d}",
                "section": s,
                "chunk_text": f"Text from {s}.",
            },
        }
        for i, s in enumerate(sections)
    ]


def _base_state(reason: str | None = None, question: str = "What is the weather?") -> dict:
    state = {
        "question": question,
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": False,
        "gate1_max_score": -1.0,
        "sub_questions": [question],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }
    if reason is not None:
        state["refusal"] = RefusalResponse(
            reason=reason,
            explanation="",
            reformulation_suggestions=[],
        )
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_normal_case_emits_two_unique_section_suggestions():
    """With 20 hits across 5 sections, node emits top-2 unique section names."""
    from agent.nodes import refuse_with_reformulation

    # 20 hits: first 4 from "Risk Factors", next 4 from "Use of Proceeds", rest from others
    sections = (
        ["Risk Factors"] * 4
        + ["Use of Proceeds"] * 4
        + ["Business Overview"] * 4
        + ["Promoter Background"] * 4
        + ["Financial Statements"] * 4
    )
    hits = _make_hits(sections)

    with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
        with patch("agent.nodes.refuse_with_reformulation.search_relaxed", return_value=hits):
            state = _base_state()
            result = refuse_with_reformulation.run(state)

    assert result["refusal"] is not None
    suggestions = result["refusal"].reformulation_suggestions
    assert len(suggestions) == 2
    assert suggestions[0] == "Risk Factors"
    assert suggestions[1] == "Use of Proceeds"


def test_single_result_case():
    """All hits from same section → suggestions list has length 1 (no padding)."""
    from agent.nodes import refuse_with_reformulation

    hits = _make_hits(["Risk Factors"] * 3)

    with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
        with patch("agent.nodes.refuse_with_reformulation.search_relaxed", return_value=hits):
            state = _base_state()
            result = refuse_with_reformulation.run(state)

    suggestions = result["refusal"].reformulation_suggestions
    assert len(suggestions) == 1
    assert suggestions[0] == "Risk Factors"


def test_empty_results_case():
    """No relaxed search results → suggestions=[], fallback message used."""
    from agent.nodes import refuse_with_reformulation

    with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
        with patch("agent.nodes.refuse_with_reformulation.search_relaxed", return_value=[]):
            state = _base_state()
            result = refuse_with_reformulation.run(state)

    assert result["refusal"] is not None
    assert result["refusal"].reformulation_suggestions == []
    assert len(result["refusal"].explanation) > 0


def test_dedupes_by_section_name():
    """Top hits all from same section → deduplicated, then second unique section."""
    from agent.nodes import refuse_with_reformulation

    sections = ["Risk Factors"] * 4 + ["Use of Proceeds"] * 3 + ["Business Overview"] * 2
    hits = _make_hits(sections)

    with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
        with patch("agent.nodes.refuse_with_reformulation.search_relaxed", return_value=hits):
            state = _base_state()
            result = refuse_with_reformulation.run(state)

    suggestions = result["refusal"].reformulation_suggestions
    assert len(suggestions) == RELAXED_SEARCH_TOP_SECTIONS
    assert suggestions[0] == "Risk Factors"
    assert suggestions[1] == "Use of Proceeds"


def test_no_llm_call():
    """RESEARCH Open Question 5: refuse_with_reformulation must be LLM-free."""
    import ast
    from pathlib import Path

    src = Path("agent/nodes/refuse_with_reformulation.py").read_text()
    tree = ast.parse(src)

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.append(node.module)

    for forbidden in ("openai", "genai", "instructor", "groq"):
        for name in imported_names:
            assert forbidden not in name, (
                f"refuse_with_reformulation.py must not import {forbidden!r} "
                f"(RESEARCH Open Question 5: LLM-free). Found in: {name!r}"
            )


def test_uses_drhp_id_default_when_filtering():
    """search_relaxed is called with drhp_id=DRHP_ID_DEFAULT."""
    from agent.nodes import refuse_with_reformulation

    with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
        with patch(
            "agent.nodes.refuse_with_reformulation.search_relaxed", return_value=[]
        ) as mock_search:
            state = _base_state()
            refuse_with_reformulation.run(state)

    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args.kwargs
    assert call_kwargs.get("drhp_id") == DRHP_ID_DEFAULT


def test_preserves_existing_refusal_reason():
    """Upstream refusal reason (gate1, cite_check, scrub) is preserved by this node."""
    from agent.nodes import refuse_with_reformulation

    hits = _make_hits(["Risk Factors", "Use of Proceeds"])

    for reason in ("low_retrieval_score", "unsupported_claim"):
        with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
            with patch(
                "agent.nodes.refuse_with_reformulation.search_relaxed", return_value=hits
            ):
                state = _base_state(reason=reason)
                result = refuse_with_reformulation.run(state)

        assert result["refusal"].reason == reason


def test_refusal_copy_uses_anchor_refusal_template():
    """The refusal message uses REFUSAL_NO_GROUNDING_TEMPLATE for non-banned-token cases."""
    from agent.nodes import refuse_with_reformulation
    from ui.copy import REFUSAL_NO_GROUNDING_TEMPLATE

    hits = _make_hits(["Risk Factors", "Use of Proceeds"])
    question = "What is the weather in Mumbai?"

    with patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024):
        with patch("agent.nodes.refuse_with_reformulation.search_relaxed", return_value=hits):
            state = _base_state(question=question)
            result = refuse_with_reformulation.run(state)

    # Message should contain the question and the section suggestions
    message = result["refusal"].explanation
    assert "Risk Factors" in message or "Use of Proceeds" in message
