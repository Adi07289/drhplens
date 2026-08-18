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

import app.util.secrets_env  # noqa: F401 — mirror Streamlit-Cloud st.secrets -> os.environ (must precede the env check below)
from agent.llm import required_key_var
from agent.policies import DEPLOY_DAILY_CAP, MIN_SECONDS_BETWEEN
from agent.schemas import FusedAnswer, GroundedAnswer, RefusalResponse
from agent.supervisor import invoke_supervisor
from data.catalogue_loader import load_catalogue
from ui.chip import render_answer_with_chips
from ui.copy import (
    EMPTY_STATE_BODY_TEMPLATE,
    EMPTY_STATE_HEADING,
    ERROR_LLM_TIMEOUT,
    HERO_HEADING_TEMPLATE,
    LOADING_ANSWER_COPY_TEMPLATE,
    QUESTION_PLACEHOLDER_TEMPLATE,
    QUOTA_CARD_BODY,
    QUOTA_CARD_HEADING,
    QUOTA_WALKTHROUGH_LINK,
    RATELIMIT_NOTICE,
)
from ui.deploy_guard import check_and_consume, is_cap_exhausted
from ui.disclaimer import render_per_answer_footer
from ui.expander import render_citation_expanders
from ui.fused_answer import render_fused_answer
from ui.methodology_pane import render_methodology_pane
from ui.refusal_banner import MAX_CHIPS_RENDERED, render_refusal_banner
from ui.state import append_to_chat_history, get_chat_history

logger = logging.getLogger(__name__)

# Provider-aware: require the ACTIVE LLM_PROVIDER's key (GROQ_API_KEY for groq,
# GEMINI_API_KEY for the gemini fallback) — not a hardcoded Gemini key.
_REQUIRED_KEY = required_key_var()
_MISSING_KEYS = [_REQUIRED_KEY] if not _os.environ.get(_REQUIRED_KEY) else []
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
                        key=f"qa_{turn_index}",
                    )

                elif isinstance(content, FusedAnswer):
                    # 06.3-08 C1/C2/C3: the multi-tool fused answer — prose-first cited
                    # paragraph + doc/tool provenance chips + honest-partial banner.
                    # Render-only (no live call on render/expand). The per-answer
                    # disclaimer wiring is preserved (D-07/D-08).
                    render_fused_answer(content, key=f"qa_{turn_index}")
                    st.markdown(render_per_answer_footer(), unsafe_allow_html=True)

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


# In-app route to the committed recorded-walkthrough surface (C4). The
# /how_it_works page is the committed, always-working plain-English walkthrough of
# the DRHP → cited-answer pipeline — an honest same-app link (dead-link-proof, no
# headless-capture tooling; consistent with the deferred-screenshots decision). Kept
# as a code constant (a route, not copy — only the link TEXT lives in ui/copy.py).
_WALKTHROUGH_HREF = "/how_it_works"


def _guard_ui_action(guard_state: str) -> str:
    """Map a ``ui.deploy_guard`` state to the mutually-exclusive C4 UI action (D-12).

    ``"cap_exhausted"`` → ``"card"`` (REPLACE the input with the fallback card);
    ``"rate_limited"`` → ``"notice"`` (a non-blocking inline notice ABOVE the input,
    which stays enabled); anything else (``"ok"``) → ``"input"`` (proceed to the
    agent). Exactly one action per state — the three are mutually exclusive."""
    if guard_state == "cap_exhausted":
        return "card"
    if guard_state == "rate_limited":
        return "notice"
    return "input"


def _render_quota_card() -> None:
    """C4 cap-exhausted fallback: a muted, dashed-neutral card that REPLACES the chat
    input and routes to the always-working read-only surfaces (snapshot/forecast/peers
    on this page, /methodology, /failures) + the recorded-walkthrough link. NOT a
    full-page interstitial — the rest of the app stays fully usable (those surfaces
    are LLM-free). No alarm-red, no countdown (honesty invariant)."""
    st.markdown(
        '<div class="drhp-quota" role="status" aria-live="polite">'
        f'<div class="drhp-quota-heading">'
        f'{html.escape(QUOTA_CARD_HEADING, quote=False)}</div>'
        f'<div class="drhp-quota-body">{html.escape(QUOTA_CARD_BODY, quote=False)}</div>'
        '<div class="drhp-quota-links">'
        f'<a href="{_WALKTHROUGH_HREF}" target="_self">'
        f'{html.escape(QUOTA_WALKTHROUGH_LINK, quote=False)}</a>'
        '<a href="/methodology" target="_self">/methodology</a>'
        '<a href="/failures" target="_self">/failures</a>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_ratelimit_notice() -> None:
    """C4 throttle: a brief muted inline notice ABOVE the (still-enabled) input. Non-
    blocking, auto-clears on the next successful send. Never alarm-red (D-12)."""
    st.markdown(
        '<div class="drhp-ratelimit" role="status" aria-live="polite">'
        f'{html.escape(RATELIMIT_NOTICE, quote=False)}</div>',
        unsafe_allow_html=True,
    )


def _render_input_and_invoke(drhp_id: str, issuer: str) -> None:
    """Chat input + agent invocation, bound to this page's drhp_id, guarded by the
    public-deploy cap/throttle (D-12)."""
    placeholder = QUESTION_PLACEHOLDER_TEMPLATE.format(issuer=issuer)

    if not _ENV_CONFIGURED:
        st.info(
            "Configure your .env to start chatting. "
            f"Missing: {', '.join(_MISSING_KEYS)}. "
            "Copy `.env.example` to `.env` and add your API keys."
        )
        st.chat_input(placeholder=placeholder, disabled=True)
        return

    # C4 (D-12): if the GLOBAL daily cap is already exhausted, REPLACE the input with
    # the fallback card before the user types — a read-only peek (no slot consumed).
    if is_cap_exhausted(DEPLOY_DAILY_CAP):
        _render_quota_card()
        return

    if st.session_state.get("draft_question"):
        st.caption(
            f'Suggested: "{st.session_state.draft_question}" '
            "— paste into the box below or type your own."
        )

    question = st.chat_input(placeholder=placeholder)
    if not question:
        return

    # C4 (D-12): the deploy guard runs BEFORE invoke_supervisor. Cap/throttle
    # short-circuits the LLM call into the C4 fallback states.
    action = _guard_ui_action(check_and_consume(DEPLOY_DAILY_CAP, MIN_SECONDS_BETWEEN))
    if action == "card":
        _render_quota_card()  # became exhausted between render and submit
        return
    if action == "notice":
        _render_ratelimit_notice()  # non-blocking; input stays enabled; not sent
        return

    st.session_state.draft_question = ""
    append_to_chat_history(st.session_state, role="user", content=question)

    loading_copy = LOADING_ANSWER_COPY_TEMPLATE.format(issuer=issuer)
    with st.status(loading_copy, state="running") as status:
        try:
            assistant_content = _invoke_agent(question, drhp_id)
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


def _invoke_agent(question: str, drhp_id: str):
    """Route the production chat through the bounded MULTI-TOOL supervisor and resolve
    its final state to a renderable assistant-content object (06.3-08).

    Replaces the Phase-1 single-tool ``invoke_with_tracing`` path: the fused answer now
    comes from ``agent.supervisor.invoke_supervisor`` (D-02/D-03), which routes across
    the read-only tools, fuses one cited answer, emits the enriched Langfuse trace, and
    crash-degrades to an honest partial (never raises — D-08). The resolver returns, in
    priority order, the fused answer (C1/C2/C3), a DRHP-only grounded answer (the
    subgraph-only path), or a refusal (nothing grounded — unchanged posture)."""
    result_state = invoke_supervisor(question, drhp_id)
    if result_state.get("fused_answer") is not None:
        return result_state["fused_answer"]
    if result_state.get("grounded_answer") is not None:
        return result_state["grounded_answer"]
    if result_state.get("refusal") is not None:
        return result_state["refusal"]
    return RefusalResponse(
        reason="infrastructure_error",
        explanation=ERROR_LLM_TIMEOUT,
        reformulation_suggestions=[],
    )


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
