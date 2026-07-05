"""
ui/snapshot_chat.py — drhp_id-parameterized Q&A chat (extracted from Phase 1
app.py per FLAG-ROUTING, 02-05-PLAN.md Task 1).

render_snapshot_chat(drhp_id) renders the metadata header, chat history,
empty state, and chat input/invocation — bound to a specific drhp_id. Called
from pages/02_snapshot.py as the co-located Q&A surface (Block 9, P2-L5).

This module intentionally has NO st.set_page_config call — that must remain
the FIRST Streamlit call in each page file (app.py / pages/02_snapshot.py).
"""
from __future__ import annotations

import html
import logging
import os as _os

import streamlit as st

from agent.graph import build_graph
from agent.schemas import GroundedAnswer, RefusalResponse
from data.catalogue_loader import load_catalogue
from ui.chip import render_answer_with_chips
from ui.copy import (
    EMPTY_STATE_BODY_TEMPLATE,
    EMPTY_STATE_HEADING,
    ERROR_LLM_TIMEOUT,
    HERO_HEADING_TEMPLATE,
    LOADING_ANSWER_COPY_TEMPLATE,
    QUESTION_PLACEHOLDER_TEMPLATE,
)
from ui.disclaimer import render_per_answer_footer
from ui.expander import render_citation_expanders
from ui.methodology_pane import render_methodology_pane
from ui.refusal_banner import MAX_CHIPS_RENDERED, render_refusal_banner
from ui.state import append_to_chat_history, get_chat_history

logger = logging.getLogger(__name__)

_MISSING_KEYS = [k for k in ["GEMINI_API_KEY"] if not _os.environ.get(k)]
_ENV_CONFIGURED = len(_MISSING_KEYS) == 0


def _issuer_for(drhp_id: str) -> str:
    """Resolve issuer display name for a drhp_id from the catalogue."""
    for ipo in load_catalogue():
        if ipo.drhp_id == drhp_id:
            return ipo.issuer
    return drhp_id


def _render_hero(issuer: str, history: list) -> None:
    """Collapsed hero line for the snapshot page (always collapsed — the
    snapshot blocks are the primary content, the chat is secondary, D2-08)."""
    heading = HERO_HEADING_TEMPLATE.format(issuer=issuer)
    st.markdown(
        f'<p class="drhp-hero-collapsed">{html.escape(heading)}</p>',
        unsafe_allow_html=True,
    )


def _render_chat_history(history: list) -> None:
    """Render all previous turns in the chat history (Phase 1 renderer, unchanged)."""
    for turn_index, turn in enumerate(history):
        with st.chat_message(turn["role"]):
            if turn["role"] == "user":
                st.markdown(html.escape(turn["content"]))
            elif turn["role"] == "assistant":
                content = turn["content"]
                if isinstance(content, GroundedAnswer):
                    rendered_html, chip_map = render_answer_with_chips(content)
                    st.markdown(rendered_html, unsafe_allow_html=True)
                    expanders = render_citation_expanders(content, chip_map)
                    for exp in expanders:
                        with st.expander(exp["label"], expanded=False):
                            st.markdown(
                                f'<div class="drhp-snippet">{exp["snippet"]}</div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f'[View DRHP page {exp["page_start"]} on SEBI →]'
                                f'({exp["source_url"]})'
                            )
                            st.markdown(
                                f'<div class="drhp-snippet-metadata">'
                                f'{exp["metadata_footer"]}</div>',
                                unsafe_allow_html=True,
                            )
                    st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
                    # METHOD-01: the primary Show-your-work surface — cached-only
                    # pane on each Q&A answer, keyed to the user's question (the
                    # immediately preceding user turn). No live call on expand.
                    prev_turn = history[turn_index - 1] if turn_index > 0 else None
                    question = (
                        prev_turn["content"]
                        if prev_turn and prev_turn["role"] == "user"
                        else ""
                    )
                    render_methodology_pane(
                        query=question,
                        grounded_answer=content,
                    )

                elif isinstance(content, RefusalResponse):
                    st.markdown(render_refusal_banner(content), unsafe_allow_html=True)
                    if (
                        content.reason != "banned_token"
                        and content.reformulation_suggestions
                    ):
                        n_chips = min(
                            len(content.reformulation_suggestions), MAX_CHIPS_RENDERED
                        )
                        cols = st.columns(n_chips)
                        for i, suggestion in enumerate(
                            content.reformulation_suggestions[:MAX_CHIPS_RENDERED]
                        ):
                            with cols[i]:
                                if st.button(
                                    suggestion,
                                    key=f"reformulate_{turn_index}_{i}",
                                    use_container_width=True,
                                ):
                                    st.session_state.draft_question = suggestion
                                    st.rerun()


def _render_empty_state(issuer: str) -> None:
    """Empty state with example question chips, parameterized by issuer."""
    st.markdown(
        f'<h2 class="drhp-empty-heading">{html.escape(EMPTY_STATE_HEADING)}</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(EMPTY_STATE_BODY_TEMPLATE.format(issuer=issuer))

    example_questions = [
        f"What does {issuer} say about its path to profitability?",
        "Who are the promoters and what is their post-issue holding?",
        "What is the use of proceeds breakdown?",
    ]
    cols = st.columns(3)
    for i, q in enumerate(example_questions):
        with cols[i]:
            if st.button(q, key=f"example_{i}", use_container_width=True):
                st.session_state.draft_question = q
                st.rerun()


def _render_input_and_invoke(drhp_id: str, issuer: str) -> None:
    """Chat input + agent invocation, bound to this page's drhp_id."""
    placeholder = QUESTION_PLACEHOLDER_TEMPLATE.format(issuer=issuer)

    if not _ENV_CONFIGURED:
        st.info(
            "Configure your .env to start chatting. "
            f"Missing: {', '.join(_MISSING_KEYS)}. "
            "Copy `.env.example` to `.env` and add your API keys."
        )
        st.chat_input(placeholder=placeholder, disabled=True)
        return

    if st.session_state.get("draft_question"):
        st.caption(
            f'Suggested: "{st.session_state.draft_question}" '
            "— paste into the box below or type your own."
        )

    question = st.chat_input(placeholder=placeholder)
    if not question:
        return

    st.session_state.draft_question = ""
    append_to_chat_history(st.session_state, role="user", content=question)

    loading_copy = LOADING_ANSWER_COPY_TEMPLATE.format(issuer=issuer)
    with st.status(loading_copy, state="running") as status:
        try:
            graph = build_graph()
            result_state = graph.invoke({
                "question": question,
                "drhp_id": drhp_id,
                "regenerate_attempts": 0,
            })
            if result_state.get("grounded_answer") is not None:
                assistant_content = result_state["grounded_answer"]
            elif result_state.get("refusal") is not None:
                assistant_content = result_state["refusal"]
            else:
                assistant_content = RefusalResponse(
                    reason="infrastructure_error",
                    explanation=ERROR_LLM_TIMEOUT,
                    reformulation_suggestions=[],
                )
            status.update(label="Done.", state="complete")
        except Exception:
            logger.exception("Agent invocation failed")
            assistant_content = RefusalResponse(
                reason="infrastructure_error",
                explanation=ERROR_LLM_TIMEOUT,
                reformulation_suggestions=[],
            )
            status.update(label="Failed.", state="error")

    append_to_chat_history(st.session_state, role="assistant", content=assistant_content)
    st.rerun()


def render_snapshot_chat(drhp_id: str) -> None:
    """Render the co-located Q&A chat for a given drhp_id (Block 9, P2-L5).

    Bound to the page's drhp_id: every graph.invoke() call passes drhp_id so
    retrieval is scoped to this IPO's DRHP. Reuses every Phase 1 surface
    (hero-collapsed line, metadata via the snapshot page's own breadcrumb/
    title, chat history, citation chips, refusal banner) unchanged.
    """
    issuer = _issuer_for(drhp_id)
    history = get_chat_history(st.session_state)

    _render_hero(issuer, history)
    _render_chat_history(history)

    if len(history) == 0:
        _render_empty_state(issuer)

    _render_input_and_invoke(drhp_id, issuer)
