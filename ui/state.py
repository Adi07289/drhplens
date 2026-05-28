"""
Session-state helpers for the Streamlit chat flow.

Designed to accept any dict-like (st.session_state, or a plain dict for unit
tests) — no `import streamlit` here. Session-scoped only per UI-SPEC
§Information Architecture §3 — no persistence across page refreshes in Phase 1.

Usage in app.py:
    from ui.state import init_session_state, has_seen_modal, mark_modal_seen, \
        append_to_chat_history, get_chat_history, reset_chat_history
    init_session_state(st.session_state)  # called once at top of app.py
"""
from __future__ import annotations

_MODAL_KEY = "disclaimer_accepted"
_HISTORY_KEY = "chat_history"
_DRAFT_KEY = "draft_question"


def init_session_state(ss) -> None:
    """Idempotent initialization of session state keys.

    Sets defaults only for keys that do not already exist. Safe to call
    on every Streamlit rerun — will not reset existing history or flags.

    Keys initialized:
        disclaimer_accepted = False
        chat_history = []
        draft_question = ""
    """
    ss.setdefault(_MODAL_KEY, False)
    ss.setdefault(_HISTORY_KEY, [])
    ss.setdefault(_DRAFT_KEY, "")


def has_seen_modal(ss) -> bool:
    """Return True if the user has dismissed the first-use modal."""
    return bool(ss.get(_MODAL_KEY, False))


def mark_modal_seen(ss) -> None:
    """Record that the user dismissed the first-use modal."""
    ss[_MODAL_KEY] = True


def append_to_chat_history(ss, role: str, content) -> None:
    """Append one turn to the chat history.

    Args:
        ss: dict-like session state
        role: "user" or "assistant"
        content: str for user turns; GroundedAnswer or RefusalResponse for assistant turns

    Raises:
        AssertionError if role is not "user" or "assistant"
    """
    assert role in ("user", "assistant"), \
        f"role must be 'user' or 'assistant', got {role!r}"
    ss[_HISTORY_KEY].append({"role": role, "content": content, "metadata": {}})


def get_chat_history(ss) -> list[dict]:
    """Return the chat history list (the same list reference — Streamlit-style).

    Returns the live list; mutating the return value mutates session state.
    Phase 1 is session-scoped only — no persistence.
    """
    return ss.get(_HISTORY_KEY, [])


def reset_chat_history(ss) -> None:
    """Clear chat history without affecting the modal-seen flag.

    Per UI-SPEC §IA §3: chat reset does not re-show the disclaimer modal.
    """
    ss[_HISTORY_KEY] = []
