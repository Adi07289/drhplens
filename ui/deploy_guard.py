"""ui/deploy_guard.py — in-process public-deploy guards for the live chat (D-12).

The public chat is genuinely live + interactive, but the Gemini free tier is the
hard ceiling. Two RELIABLE, in-process controls bound it (no external rate-limit
service — CLAUDE.md free-tier-only):

  * a GLOBAL daily cap via ``@st.cache_resource`` — one shared counter object per
    Space *process* (survives Streamlit reruns; resets on cold start). App-wide, not
    per-user, so it is the control that actually protects the free-tier RPD
    (T-6.3-DoS, the anti-abuse boundary). Rolls over at local midnight.
  * a per-SESSION throttle via ``st.session_state`` — a last-question timestamp that
    rate-limits bursts from one browser session (reliable — session_state is the one
    session primitive that behaves on HF Spaces).

**Per-IP is NOT a control here.** Behind the HF Spaces proxy ``st.context.ip_address``
returns ``None`` (the proxy terminates the connection; the runtime ``remote_ip`` only
ever sees the proxy), so a per-IP cap would be trivially defeated or wrongly-shared
and is documented UNRELIABLE (RESEARCH A4 / T-6.3-IP, disposition = accept). The
global cap + per-session throttle work regardless of the proxy. A best-effort IP tag
could be logged for observability, but it is never the primary control.

The single entry point is :func:`check_and_consume`, returning exactly one of three
mutually-exclusive states — ``"cap_exhausted" | "rate_limited" | "ok"`` — that the
chat surface maps to the three C4 UI states (fallback card / inline notice / normal
input). The cap VALUE + throttle window live in ``agent/policies.py`` (a re-verified
~20-RPD-sourced constant, NOT the stale 1500/day — RESEARCH Pitfall 7); this module
holds the mechanism only.
"""
from __future__ import annotations

import datetime as _dt
import time as _time

import streamlit as st

from agent.policies import DEPLOY_DAILY_CAP, MIN_SECONDS_BETWEEN

# The per-session last-question timestamp key (st.session_state). Namespaced so it
# never collides with the app's other session keys (ui/state.py).
_SESSION_TS_KEY = "_drhp_deploy_last_q_ts"


def _now() -> float:
    """Monotonic-enough wall clock for the throttle window (wrapped so tests can
    control it without patching the stdlib)."""
    return _time.time()


def _today() -> str:
    """Local calendar date as an ISO string — the daily-cap rollover key (wrapped
    so tests can advance the date deterministically)."""
    return _dt.date.today().isoformat()


@st.cache_resource
def _global_counter() -> dict:
    """The process-global daily counter — ONE shared dict per Space process.

    ``@st.cache_resource`` returns the same object across every rerun and every user
    session in the process, which is exactly what an APP-WIDE cap needs (it is not
    per-user). It is best-effort: a HF cold start restarts the process and resets the
    count to zero, which is acceptable — the cap protects a *daily* free-tier budget,
    and a cold start already implies a quiet period. The ``{date, count}`` shape rolls
    the count over when the calendar date changes.
    """
    return {"date": _today(), "count": 0}


def is_cap_exhausted(daily_cap: int = DEPLOY_DAILY_CAP) -> bool:
    """Read-only PEEK: is the global daily cap already exhausted for today?

    Used to decide whether to render the C4 fallback card IN PLACE OF the chat input
    (before the user types) — so it must NOT mutate the counter. A date rollover is
    treated as not-exhausted here; the actual reset happens on the next
    :func:`check_and_consume` (the one place that mutates).
    """
    counter = _global_counter()
    if counter.get("date") != _today():
        return False
    return counter.get("count", 0) >= daily_cap


def check_and_consume(
    daily_cap: int = DEPLOY_DAILY_CAP,
    min_seconds: float = MIN_SECONDS_BETWEEN,
) -> str:
    """Guard a live chat submission, returning exactly one of three states.

    Called BEFORE ``invoke_supervisor`` on every question submit:

      * ``"cap_exhausted"`` — the global daily cap is reached (checked FIRST, so it
        wins over a throttle). No slot is consumed. → C4 fallback card replaces input.
      * ``"rate_limited"`` — this session asked again within ``min_seconds``. No slot
        is consumed (a throttled question never burns the daily budget). → C4 inline
        notice above the input, which STAYS enabled.
      * ``"ok"`` — under the cap and outside the throttle window: stamps the session
        timestamp, increments the global counter, and returns. → proceed to the LLM.

    Order matters: cap → throttle → consume. The three returns are mutually exclusive
    (one string), which is what makes the three C4 UI states mutually exclusive too.
    """
    counter = _global_counter()
    today = _today()
    if counter.get("date") != today:  # midnight rollover
        counter["date"] = today
        counter["count"] = 0

    if counter.get("count", 0) >= daily_cap:
        return "cap_exhausted"

    last = st.session_state.get(_SESSION_TS_KEY, 0.0)
    if _now() - last < min_seconds:
        return "rate_limited"

    st.session_state[_SESSION_TS_KEY] = _now()
    counter["count"] = counter.get("count", 0) + 1
    return "ok"
