"""
DRHPLens Streamlit entry point.

Wraps the Wave 3 LangGraph agent in the UI-SPEC-compliant chat interface:
hero (expanded/collapsed), DRHP metadata header, chat history with citation
chips + inline expanders, refusal banner, persistent footer, first-use modal.

UI-01 (mobile-responsive) + UI-02 (citation chips clickable) are wired here.
"""
import html
import logging

import streamlit as st

# ── Page config (MUST be the first Streamlit call) ───────────────────────────
st.set_page_config(
    page_title="DRHPLens · Ask about Swiggy",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

from agent.graph import build_graph  # noqa: E402
from agent.schemas import GroundedAnswer, RefusalResponse  # noqa: E402
from app.util.css_loader import load_global_css  # noqa: E402
from compliance.disclaimer_text import MODAL_HEADING  # noqa: E402
from ui.chip import render_answer_with_chips  # noqa: E402
from ui.copy import (  # noqa: E402
    EMPTY_STATE_BODY,
    EMPTY_STATE_HEADING,
    ERROR_LLM_TIMEOUT,
    ERROR_QDRANT_UNREACHABLE,
    HERO_HEADING,
    HERO_SUBHEADING,
    LOADING_ANSWER_COPY,
    QUESTION_PLACEHOLDER,
)
from ui.disclaimer import (  # noqa: E402
    render_first_use_modal,
    render_per_answer_footer,
    render_persistent_footer,
)
from ui.expander import SEBI_PROSPECTUS_URL, render_citation_expanders  # noqa: E402
from ui.refusal_banner import MAX_CHIPS_RENDERED, render_refusal_banner  # noqa: E402
from ui.state import (  # noqa: E402
    append_to_chat_history,
    get_chat_history,
    has_seen_modal,
    init_session_state,
    mark_modal_seen,
)

logger = logging.getLogger(__name__)

# ── Graceful missing-env guard ────────────────────────────────────────────────
import os as _os  # noqa: E402

_MISSING_KEYS = [k for k in ["GEMINI_API_KEY"] if not _os.environ.get(k)]
_ENV_CONFIGURED = len(_MISSING_KEYS) == 0


def _load_css() -> None:
    """Load global CSS once per session (UI-SPEC FLAG-2)."""
    css_html = load_global_css(st.session_state)
    if css_html:
        st.markdown(css_html, unsafe_allow_html=True)


def _set_lang() -> None:
    """Set HTML lang attribute for screen readers.

    ## FLAG-LANG-ATTR: Streamlit 1.36 has no config for <html lang>. This JS
    workaround runs after first render. Phase 6 may use Streamlit Components.
    """
    st.markdown(
        '<script>document.documentElement.lang = "en-IN";</script>',
        unsafe_allow_html=True,
    )


def _show_modal_gate() -> None:
    """First-use modal — shown once per session (UI-SPEC §Disclaimer Surfaces §1).

    Acceptance is intentional, single-step. No close X (UI-SPEC anti-pattern).
    """
    @st.dialog(MODAL_HEADING)
    def _first_use_modal() -> None:
        data = render_first_use_modal()
        st.markdown(data["body"])
        if st.button(data["cta_text"], type="primary", use_container_width=True):
            mark_modal_seen(st.session_state)
            st.rerun()

    if not has_seen_modal(st.session_state):
        _first_use_modal()
        st.stop()


def _render_hero(history: list) -> None:
    """Hero block — expanded (no history) or collapsed (has history).

    UI-SPEC §IA §1 and §1a: instant swap, no animation.
    # UI-SPEC §IA §1a: instant swap, no animation. prefers-reduced-motion
    # already respected via Task 1 CSS.
    """
    if len(history) == 0:
        # Expanded hero: Display 28px heading + subheading
        st.markdown(
            f'<h1 class="drhp-hero-display">{html.escape(HERO_HEADING)}</h1>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="drhp-hero-subheading">{html.escape(HERO_SUBHEADING)}</p>',
            unsafe_allow_html=True,
        )
    else:
        # Collapsed hero: single body-size line
        st.markdown(
            f'<p class="drhp-hero-collapsed">{html.escape(HERO_HEADING)}</p>',
            unsafe_allow_html=True,
        )


def _render_metadata_header() -> None:
    """DRHP metadata header (UI-SPEC §IA §2) — Surface-secondary block.

    ## FLAG-ISSUE-SIZE: ₹11,327 cr is from the Swiggy DRHP cover page
    (Total Issue Size including OFS as stated in the DRHP).
    Wave 5 planner: verify against committed PDF before HF Spaces launch.

    rel="noopener" on external link per ASVS V12 tabnabbing mitigation (T-1-13).
    """
    # UI-SPEC §Color: accent #1E40AF is reserved for chips + chip focus +
    # methodology link + chat-input focus + modal CTA. Do not paint other
    # interactive elements this color.
    st.markdown(
        f'''<div class="drhp-metadata-header">
  <span class="drhp-metadata-label">Issuer ·</span>
  <span class="drhp-metadata-value">Swiggy Limited</span> &nbsp;·&nbsp;
  <span class="drhp-metadata-label">Issue size ·</span>
  <span class="drhp-metadata-value">₹11,327 cr</span> &nbsp;·&nbsp;
  <span class="drhp-metadata-label">Listed ·</span>
  <span class="drhp-metadata-value">Nov 2024</span> &nbsp;·&nbsp;
  <span class="drhp-metadata-label">DRHP source ·</span>
  <a class="drhp-footer-link" href="{SEBI_PROSPECTUS_URL}"
     target="_blank" rel="noopener">SEBI</a>
</div>''',
        unsafe_allow_html=True,
    )


def _render_chat_history(history: list) -> None:
    """Render all previous turns in the chat history.

    UI-SPEC §IA §3: user turns as right-aligned bubbles; assistant turns
    as grounded answer (chips + expanders + footer) or refusal banner.

    # UI-SPEC anti-pattern: do NOT replace render_refusal_banner with st.warning
    # or st.error — refusals are first-class output, not chrome.
    """
    for turn_index, turn in enumerate(history):
        with st.chat_message(turn["role"]):
            if turn["role"] == "user":
                # User turn: plain text; html.escape as defense-in-depth
                st.markdown(html.escape(turn["content"]))
            elif turn["role"] == "assistant":
                content = turn["content"]
                if isinstance(content, GroundedAnswer):
                    # Render prose with citation chips (Task 2)
                    rendered_html, chip_map = render_answer_with_chips(content)
                    st.markdown(rendered_html, unsafe_allow_html=True)
                    # One expander per unique citation (Task 2)
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
                    # Per-answer disclaimer (Task 3)
                    st.markdown(render_per_answer_footer(), unsafe_allow_html=True)

                elif isinstance(content, RefusalResponse):
                    # Render refusal banner (has its OWN per-answer footer baked in)
                    # Do NOT also append render_per_answer_footer here.
                    st.markdown(render_refusal_banner(content), unsafe_allow_html=True)
                    # Reformulation chip click handlers — functional Streamlit buttons
                    # (visual HTML chips are inside the banner; these are the click targets)
                    # UI-SPEC §Streamlit-Specific Constraints reformulation-chip row
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


def _render_empty_state() -> None:
    """Empty state with example question chips (UI-SPEC §IA §5).

    Clicking fills the input; does NOT auto-submit (user retains agency).
    """
    st.markdown(
        f'<h2 class="drhp-empty-heading">{html.escape(EMPTY_STATE_HEADING)}</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(EMPTY_STATE_BODY)

    example_questions = [
        "What does Swiggy say about its path to profitability?",
        "Who are the promoters and what is their post-issue holding?",
        "What is the use of proceeds breakdown?",
    ]
    cols = st.columns(3)
    for i, q in enumerate(example_questions):
        with cols[i]:
            if st.button(q, key=f"example_{i}", use_container_width=True):
                st.session_state.draft_question = q
                st.rerun()


def _render_input_and_invoke() -> None:
    """Chat input + agent invocation (UI-SPEC §IA §4 + §Loading).

    If env vars are missing, shows a configure banner instead of crashing
    (app.py must boot cleanly on a fresh HF Spaces visit without .env).
    """
    if not _ENV_CONFIGURED:
        st.info(
            "Configure your .env to start chatting. "
            f"Missing: {', '.join(_MISSING_KEYS)}. "
            "Copy `.env.example` to `.env` and add your API keys."
        )
        # Still render the input so the page is navigable
        st.chat_input(placeholder=QUESTION_PLACEHOLDER, disabled=True)
        return

    # Draft question helper line (st.chat_input does not support default value)
    if st.session_state.get("draft_question"):
        st.caption(
            f'Suggested: "{st.session_state.draft_question}" '
            "— paste into the box below or type your own."
        )

    question = st.chat_input(placeholder=QUESTION_PLACEHOLDER)
    if not question:
        return

    st.session_state.draft_question = ""
    append_to_chat_history(st.session_state, role="user", content=question)

    # Agent invocation with st.status loading state (UI-SPEC §Loading/Empty/Error)
    with st.status(LOADING_ANSWER_COPY, state="running") as status:
        try:
            graph = build_graph()
            result_state = graph.invoke({
                "question": question,
                "regenerate_attempts": 0,
            })
            if result_state.get("grounded_answer") is not None:
                assistant_content = result_state["grounded_answer"]
            elif result_state.get("refusal") is not None:
                assistant_content = result_state["refusal"]
            else:
                # Safety net: agent returned neither (T-1-04 — no raw errors to user)
                assistant_content = RefusalResponse(
                    reason="infrastructure_error",
                    explanation=ERROR_LLM_TIMEOUT,
                    reformulation_suggestions=[],
                )
            status.update(label="Done.", state="complete")
        except Exception:
            logger.exception("Agent invocation failed")
            # T-1-04: raw str(e) logged server-side, never rendered to user
            error_msg = ERROR_LLM_TIMEOUT
            assistant_content = RefusalResponse(
                reason="infrastructure_error",
                explanation=error_msg,
                reformulation_suggestions=[],
            )
            status.update(label="Failed.", state="error")

    append_to_chat_history(st.session_state, role="assistant", content=assistant_content)
    st.rerun()


def main() -> None:
    """Main app entry point — linear top-to-bottom rendering."""
    # Set lang attribute (Phase 6 polish — see FLAG-LANG-ATTR)
    _set_lang()

    # Load global CSS (idempotent, UI-SPEC FLAG-2)
    _load_css()

    # Initialize session state (idempotent)
    init_session_state(st.session_state)

    # First-use modal gate (stops page render until accepted)
    _show_modal_gate()

    # Get history for hero branching
    history = get_chat_history(st.session_state)

    # Hero (expanded when no history, collapsed after first message)
    _render_hero(history)

    # DRHP metadata header (always visible)
    _render_metadata_header()

    # Chat history
    _render_chat_history(history)

    # Empty state (pre-first-question only)
    if len(history) == 0:
        _render_empty_state()

    # Question input + agent invocation
    _render_input_and_invoke()

    # Persistent footer (always visible, sticky on mobile)
    st.markdown(render_persistent_footer(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
else:
    # Streamlit runs the module top-to-bottom; call main() unconditionally
    main()
