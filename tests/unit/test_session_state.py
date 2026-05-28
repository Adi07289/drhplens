"""
TDD Task 4 — ui/state.py

Tests session-state helpers using plain dict as stand-in for st.session_state.
No Streamlit dependency in this test file.
"""
from __future__ import annotations

import pytest

from ui.state import (
    append_to_chat_history,
    get_chat_history,
    has_seen_modal,
    init_session_state,
    mark_modal_seen,
    reset_chat_history,
)


# ── init_session_state ────────────────────────────────────────────────────────

def test_init_session_state_idempotent() -> None:
    ss: dict = {}
    init_session_state(ss)
    assert ss["disclaimer_accepted"] is False
    assert ss["chat_history"] == []
    assert ss["draft_question"] == ""

    # Second call must not reset
    ss["disclaimer_accepted"] = True
    ss["chat_history"] = [{"role": "user"}]
    init_session_state(ss)
    assert ss["disclaimer_accepted"] is True
    assert len(ss["chat_history"]) == 1


def test_init_session_state_preserves_existing_history() -> None:
    existing = [{"role": "user", "content": "x"}]
    ss = {"chat_history": existing}
    init_session_state(ss)
    assert ss["chat_history"] is existing
    assert len(ss["chat_history"]) == 1


# ── has_seen_modal / mark_modal_seen ─────────────────────────────────────────

def test_has_seen_modal_default_false() -> None:
    ss: dict = {}
    init_session_state(ss)
    assert has_seen_modal(ss) is False


def test_has_seen_modal_returns_true_after_mark() -> None:
    ss: dict = {}
    init_session_state(ss)
    mark_modal_seen(ss)
    assert has_seen_modal(ss) is True


# ── append_to_chat_history ────────────────────────────────────────────────────

def test_chat_history_append_user_turn() -> None:
    ss: dict = {}
    init_session_state(ss)
    append_to_chat_history(ss, role="user", content="What is the issue size?")
    history = get_chat_history(ss)
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is the issue size?"
    assert history[0]["metadata"] == {}


def test_chat_history_append_assistant_turn_with_grounded_answer() -> None:
    from agent.schemas import Claim, GroundedAnswer, RetrievedChunkRef
    ref = RetrievedChunkRef(
        chunk_id="c1", page_start=1, page_end=2, section="Risk Factors",
        verbatim_span="text",
    )
    claim = Claim(
        claim_id="c_aaaaaa", text="fact", source_chunk_id="c1",
        drhp_page=1, section="Risk Factors",
        verbatim_span="text", span_offsets=(0, 4),
        sources=[ref],
    )
    answer = GroundedAnswer(answer_prose="Fact.{{c_aaaaaa}}", claims=[claim])

    ss: dict = {}
    init_session_state(ss)
    append_to_chat_history(ss, role="assistant", content=answer)
    history = get_chat_history(ss)
    assert len(history) == 1
    assert history[0]["role"] == "assistant"
    assert history[0]["content"] is answer


def test_chat_history_append_assistant_turn_with_refusal() -> None:
    from agent.schemas import RefusalResponse
    refusal = RefusalResponse(
        reason="low_retrieval_score",
        explanation="Not in DRHP.",
        reformulation_suggestions=[],
    )
    ss: dict = {}
    init_session_state(ss)
    append_to_chat_history(ss, role="assistant", content=refusal)
    history = get_chat_history(ss)
    assert history[0]["content"] is refusal


# ── get_chat_history ──────────────────────────────────────────────────────────

def test_get_chat_history_returns_list_reference() -> None:
    ss: dict = {}
    init_session_state(ss)
    history = get_chat_history(ss)
    # Mutating return value mutates state
    history.append({"role": "user", "content": "q"})
    assert len(ss["chat_history"]) == 1


# ── reset_chat_history ────────────────────────────────────────────────────────

def test_reset_chat_history_clears_but_preserves_modal_seen() -> None:
    ss: dict = {}
    init_session_state(ss)
    mark_modal_seen(ss)
    append_to_chat_history(ss, role="user", content="q1")
    append_to_chat_history(ss, role="user", content="q2")

    reset_chat_history(ss)
    assert get_chat_history(ss) == []
    assert has_seen_modal(ss) is True, "Modal flag must survive chat reset"


# ── no streamlit import ───────────────────────────────────────────────────────

def test_helpers_accept_plain_dict_no_streamlit_import() -> None:
    import ui.state
    import sys
    # ui.state itself must not have imported streamlit at module level
    # Check code lines only (not docstring/comment lines)
    source_imports = [
        line for line in open(ui.state.__file__).readlines()
        if line.lstrip().startswith("import streamlit") or
           line.lstrip().startswith("from streamlit")
    ]
    assert not source_imports, \
        f"ui/state.py must not import streamlit: {source_imports}"

    # Works with plain dict
    result = has_seen_modal({"disclaimer_accepted": True})
    assert result is True
