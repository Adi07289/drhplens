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

import html
import inspect
import re
from pathlib import Path

import yaml

import ui.deploy_guard as deploy_guard
from agent import policies

_REPO = Path(__file__).resolve().parents[2]
_CSS_PATH = _REPO / "app" / "static" / "drhplens.css"
_PING_PATH = _REPO / ".github" / "workflows" / "ping.yml"
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


# ═══════════════════════════════════════════════════════════════════════════
# Task 2 — the C4 fallback WIRING (guard states → mutually-exclusive UI states),
# the keep-warm pinger, and the no-verdict-colour C4 CSS block.
# ═══════════════════════════════════════════════════════════════════════════

import ui.snapshot_chat as snapshot_chat  # noqa: E402
from agent.schemas import GroundedAnswer  # noqa: E402
from ui.copy import (  # noqa: E402
    QUOTA_CARD_HEADING,
    QUOTA_WALKTHROUGH_LINK,
    RATELIMIT_NOTICE,
)


class _Rerun(Exception):
    """Sentinel raised by the fake ``st.rerun`` to halt the script (as Streamlit does)."""


class _StatusCtx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def update(self, *a, **k):
        return None


class _SessionState(dict):
    """dict that also supports attribute access (mirrors st.session_state)."""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AttributeError(k) from exc

    def __setattr__(self, k, v):
        self[k] = v


class _ChatFakeSt:
    """Records markdown bodies + whether the chat input was rendered."""

    def __init__(self, chat_return=None):
        self.session_state = _SessionState()
        self.emitted: list[str] = []
        self.chat_calls = 0
        self._chat_return = chat_return

    def markdown(self, body, unsafe_allow_html=False):
        self.emitted.append(body)

    def caption(self, text):
        self.emitted.append(text)

    def info(self, text):
        self.emitted.append(text)

    def chat_input(self, placeholder=None, disabled=False):
        self.chat_calls += 1
        return self._chat_return

    def status(self, label, state=None):
        return _StatusCtx()

    def rerun(self):
        raise _Rerun()

    @property
    def body(self) -> str:
        return "".join(self.emitted)


def _prep(monkeypatch, *, cap_exhausted, guard_state, chat_return):
    monkeypatch.setattr(snapshot_chat, "_ENV_CONFIGURED", True)
    monkeypatch.setattr(snapshot_chat, "is_cap_exhausted", lambda cap: cap_exhausted)
    monkeypatch.setattr(snapshot_chat, "check_and_consume", lambda cap, secs: guard_state)
    fake = _ChatFakeSt(chat_return=chat_return)
    monkeypatch.setattr(snapshot_chat, "st", fake)
    invoked = {"n": 0}

    def _fake_invoke(question, drhp_id):
        invoked["n"] += 1
        return GroundedAnswer(answer_prose="ok", claims=[])

    monkeypatch.setattr(snapshot_chat, "_invoke_agent", _fake_invoke)
    monkeypatch.setattr(snapshot_chat, "append_to_chat_history", lambda *a, **k: None)
    return fake, invoked


# ── the three guard states are mutually-exclusive UI actions ─────────────────
def test_guard_ui_action_is_mutually_exclusive():
    """Each guard state maps to exactly one of the three C4 UI actions."""
    m = snapshot_chat._guard_ui_action
    assert m("cap_exhausted") == "card"
    assert m("rate_limited") == "notice"
    assert m("ok") == "input"
    assert {m("cap_exhausted"), m("rate_limited"), m("ok")} == {"card", "notice", "input"}


def test_cap_exhausted_replaces_the_input_with_the_card(monkeypatch):
    """Cap exhausted → the C4 fallback card is rendered and the chat input is NOT
    rendered (replaced), and the LLM is never called."""
    fake, invoked = _prep(monkeypatch, cap_exhausted=True, guard_state="ok", chat_return=None)
    snapshot_chat._render_input_and_invoke("swiggy_2024_11", "Swiggy")
    assert "drhp-quota" in fake.body  # fallback card present
    assert fake.chat_calls == 0  # input REPLACED, not rendered
    assert invoked["n"] == 0  # no LLM call


def test_rate_limited_shows_inline_notice_and_keeps_input(monkeypatch):
    """Throttled → the inline notice renders, the input STAYS enabled, no LLM call."""
    fake, invoked = _prep(
        monkeypatch, cap_exhausted=False, guard_state="rate_limited", chat_return="q?"
    )
    snapshot_chat._render_input_and_invoke("swiggy_2024_11", "Swiggy")
    assert "drhp-ratelimit" in fake.body  # non-blocking inline notice
    assert "drhp-quota" not in fake.body  # not the card
    assert fake.chat_calls == 1  # input stays enabled
    assert invoked["n"] == 0  # question NOT sent to the LLM


def test_ok_proceeds_to_invoke_supervisor(monkeypatch):
    """OK → no card, no notice; the question reaches the (multi-tool) agent."""
    fake, invoked = _prep(
        monkeypatch, cap_exhausted=False, guard_state="ok", chat_return="q?"
    )
    try:
        snapshot_chat._render_input_and_invoke("swiggy_2024_11", "Swiggy")
    except _Rerun:
        pass  # the ok path ends in st.rerun()
    assert invoked["n"] == 1  # reached the agent
    assert "drhp-quota" not in fake.body
    assert "drhp-ratelimit" not in fake.body


def test_guard_runs_before_invoke_supervisor():
    """Acceptance grep: the guard is wired into the chat surface before the agent."""
    src = inspect.getsource(snapshot_chat)
    assert src.count("check_and_consume") >= 1
    fn = inspect.getsource(snapshot_chat._render_input_and_invoke)
    assert fn.index("check_and_consume") < fn.index("_invoke_agent")


# ── the C4 card + notice render the centralized copy ─────────────────────────
class _RecSt:
    def __init__(self):
        self.emitted: list[str] = []

    def markdown(self, body, unsafe_allow_html=False):
        self.emitted.append(body)

    @property
    def body(self):
        return "".join(self.emitted)


def test_quota_card_render_routes_to_readonly_surfaces(monkeypatch):
    rec = _RecSt()
    monkeypatch.setattr(snapshot_chat, "st", rec)
    snapshot_chat._render_quota_card()
    body = html.unescape(rec.body)
    assert "drhp-quota" in rec.body
    assert QUOTA_CARD_HEADING in body
    assert "Everything else still works" in body  # QUOTA_CARD_BODY
    assert QUOTA_WALKTHROUGH_LINK in body
    # routes to the always-working read-only surfaces (in-app routes, dead-link-proof)
    assert "/methodology" in rec.body
    assert "/failures" in rec.body
    assert "/how_it_works" in rec.body  # the committed recorded-walkthrough surface


def test_ratelimit_notice_render(monkeypatch):
    rec = _RecSt()
    monkeypatch.setattr(snapshot_chat, "st", rec)
    snapshot_chat._render_ratelimit_notice()
    assert "drhp-ratelimit" in rec.body
    assert RATELIMIT_NOTICE in html.unescape(rec.body)


# ── the keep-warm pinger (P19) ───────────────────────────────────────────────
def test_ping_workflow_is_well_formed_with_schedule():
    """.github/workflows/ping.yml exists, parses as YAML, and has a schedule cron."""
    assert _PING_PATH.exists()
    text = _PING_PATH.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)  # raises on malformed YAML
    assert isinstance(doc, dict)
    # GitHub maps the ``on:`` key to the YAML 1.1 boolean True — accept either form.
    trigger = doc.get("on", doc.get(True))
    assert isinstance(trigger, dict) and "schedule" in trigger
    assert re.search(r"cron:\s*[\"']?\*/8", text)  # every ~8 min keep-warm


# ── no verdict colour in the C4 CSS block (honesty invariant) ────────────────
_CSS_OPEN = "/* === PHASE 6.3 · quota/rate-limit fallback additive classes"
_CSS_CLOSE = "=== END PHASE 6.3 · quota/rate-limit fallback additive classes === */"


def _c4_css_block() -> str:
    css = _CSS_PATH.read_text(encoding="utf-8")
    assert _CSS_OPEN in css and _CSS_CLOSE in css  # block present (not vacuous)
    return css[css.index(_CSS_OPEN):css.index(_CSS_CLOSE) + len(_CSS_CLOSE)]


def test_quota_css_block_has_no_verdict_color_token():
    block = _c4_css_block()
    declarations = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL).lower()
    forbidden = (
        "--drhp-refusal", "red", "green", "crimson", "danger", "success",
        "destructive", "#dc2626", "#ef4444", "#f87171", "#16a34a", "#22c55e",
    )
    for token in forbidden:
        assert token not in declarations, (
            f"the C4 quota/rate-limit CSS block must not use the verdict token {token!r}"
        )


def test_quota_css_uses_space_tokens_and_declares_classes():
    block = _c4_css_block()
    for cls in (".drhp-quota", ".drhp-quota-links", ".drhp-ratelimit"):
        assert cls in block, f"missing additive C4 class {cls}"
    assert "var(--drhp-space-" in block  # spacing via the declared tokens
