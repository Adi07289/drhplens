"""Unit tests — the public-deploy guards (D-12, 06.3-09).

Task 1 (this block): pins the in-process guard mechanism in ``ui.deploy_guard`` —
the GLOBAL daily cap (``@st.cache_resource``) + the per-session throttle
(``st.session_state``), both OFFLINE (the clock, the global counter, and
session_state are all monkeypatched — no Streamlit runtime, no network, no quota
burn). Asserts the three mutually-exclusive states, the cap ceiling, the throttle
window, the ``"ok"`` consume, and the date rollover; plus the two acceptance
invariants (per-IP documented unreliable behind the HF proxy; the cap VALUE is a
re-verified policies constant, NOT the stale 1500/day figure).

Task 2 (appended below the divider): pins the C4 fallback WIRING in
``ui.snapshot_chat`` (three guard states → three mutually-exclusive UI states), the
keep-warm ``ping.yml``, and the no-verdict-colour C4 CSS block.
"""
from __future__ import annotations

import inspect

import ui.deploy_guard as deploy_guard
from agent import policies

_SESSION_KEY = "_drhp_deploy_last_q_ts"


# ---------------------------------------------------------------------------
# Offline harness — swap the global counter, session_state, and clock so the
# guard is fully deterministic with no Streamlit runtime.
# ---------------------------------------------------------------------------


class _FakeSt:
    """Minimal Streamlit stub exposing only ``session_state`` (a dict)."""

    def __init__(self) -> None:
        self.session_state: dict = {}


def _setup(monkeypatch, *, count=0, date="2026-08-13", session_ts=None, now=1000.0):
    counter = {"date": date, "count": count}
    fake = _FakeSt()
    if session_ts is not None:
        fake.session_state[_SESSION_KEY] = session_ts
    clock = {"t": now}
    monkeypatch.setattr(deploy_guard, "_global_counter", lambda: counter)
    monkeypatch.setattr(deploy_guard, "st", fake)
    monkeypatch.setattr(deploy_guard, "_today", lambda: date)
    monkeypatch.setattr(deploy_guard, "_now", lambda: clock["t"])
    return counter, fake, clock


# ── the global daily cap ─────────────────────────────────────────────────────
def test_cap_exhausted_at_cap(monkeypatch):
    """At/above the cap → ``"cap_exhausted"``; the counter is NOT pushed past the cap."""
    counter, _fake, _clock = _setup(monkeypatch, count=4)
    assert deploy_guard.check_and_consume(4, 4.0) == "cap_exhausted"
    assert counter["count"] == 4  # cap-exhausted consumes no slot


def test_under_cap_ok_increments_global_counter(monkeypatch):
    """A spaced call under the cap → ``"ok"``, increments the GLOBAL counter, and
    stamps the per-session timestamp."""
    counter, fake, clock = _setup(monkeypatch, count=1)
    assert deploy_guard.check_and_consume(4, 4.0) == "ok"
    assert counter["count"] == 2  # global counter advanced
    assert fake.session_state[_SESSION_KEY] == clock["t"]  # session ts stamped


# ── the per-session throttle ─────────────────────────────────────────────────
def test_rate_limited_within_window(monkeypatch):
    """A second question within ``min_seconds`` → ``"rate_limited"`` and consumes NO
    daily-cap slot (a throttled burst never burns the free-tier budget)."""
    counter, _fake, _clock = _setup(monkeypatch, count=1, session_ts=999.0, now=1001.0)
    assert deploy_guard.check_and_consume(4, 4.0) == "rate_limited"  # 2s < 4s window
    assert counter["count"] == 1  # not consumed


def test_spaced_call_outside_window_is_ok(monkeypatch):
    """The same session, spaced beyond the window → ``"ok"`` (consumes)."""
    counter, _fake, _clock = _setup(monkeypatch, count=1, session_ts=990.0, now=1000.0)
    assert deploy_guard.check_and_consume(4, 4.0) == "ok"  # 10s > 4s window
    assert counter["count"] == 2


def test_cap_wins_over_throttle(monkeypatch):
    """Cap is checked before the throttle — an exhausted cap returns
    ``"cap_exhausted"`` even inside the throttle window."""
    _counter, _fake, _clock = _setup(monkeypatch, count=4, session_ts=999.0, now=1000.0)
    assert deploy_guard.check_and_consume(4, 4.0) == "cap_exhausted"


# ── the midnight rollover ────────────────────────────────────────────────────
def test_counter_rolls_over_on_new_date(monkeypatch):
    """A new calendar date resets the global counter (was at cap yesterday → ``"ok"``
    today, count starts fresh at 1)."""
    counter, _fake, _clock = _setup(monkeypatch, count=4, date="2026-08-12")
    monkeypatch.setattr(deploy_guard, "_today", lambda: "2026-08-13")  # new day
    assert deploy_guard.check_and_consume(4, 4.0) == "ok"
    assert counter["date"] == "2026-08-13"
    assert counter["count"] == 1


# ── the read-only peek (used to replace the input before the user types) ─────
def test_is_cap_exhausted_peek_does_not_mutate(monkeypatch):
    counter, _fake, _clock = _setup(monkeypatch, count=4)
    assert deploy_guard.is_cap_exhausted(4) is True
    assert counter["count"] == 4  # peek never mutates
    counter["count"] = 3
    assert deploy_guard.is_cap_exhausted(4) is False


def test_is_cap_exhausted_new_date_is_not_exhausted(monkeypatch):
    counter, _fake, _clock = _setup(monkeypatch, count=4, date="2026-08-12")
    monkeypatch.setattr(deploy_guard, "_today", lambda: "2026-08-13")
    assert deploy_guard.is_cap_exhausted(4) is False  # rollover → fresh


# ── acceptance: per-IP documented unreliable; not the primary control ────────
def test_module_documents_per_ip_unreliable_behind_proxy():
    """The module MUST document per-IP as unreliable behind the HF proxy and NOT the
    primary control (RESEARCH A4 / T-6.3-IP)."""
    src = inspect.getsource(deploy_guard).lower()
    assert "ip_address" in src
    assert "proxy" in src
    assert "per-ip is not a control" in src
    # the two reliable controls are named as such
    assert "global daily cap" in src
    assert "per-session throttle" in src


# ── acceptance: the cap VALUE is a re-verified policies constant, not 1500 ────
def test_policies_define_deploy_constants_not_stale_1500():
    assert isinstance(policies.DEPLOY_DAILY_CAP, int)
    assert policies.DEPLOY_DAILY_CAP >= 1
    assert policies.DEPLOY_DAILY_CAP != 1500  # NOT the stale CLAUDE.md figure
    assert isinstance(policies.MIN_SECONDS_BETWEEN, float)
    assert policies.MIN_SECONDS_BETWEEN > 0
    src = inspect.getsource(policies).lower()
    # docstring cites the re-verified RPD source + the re-verify-at-deploy posture
    assert "re-verify" in src
    assert "assumed" in src
    assert "1500" in src  # cited only to REJECT it as stale
