"""
TDD Task 1 — app/static/drhplens.css + app/util/css_loader.py

Tests the global CSS contract (UI-SPEC COLOR/TYPOGRAPHY/SPACING/BREAKPOINTS/
ACCESSIBILITY) and the single-load idempotent injector.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS_PATH = Path("app/static/drhplens.css")


@pytest.fixture(scope="module")
def css_text() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


# ── File existence + size ────────────────────────────────────────────────────

def test_css_file_exists_and_nonempty(css_text: str) -> None:
    assert CSS_PATH.exists(), "app/static/drhplens.css missing"
    assert len(css_text) > 2000, f"CSS too small ({len(css_text)} chars) — all sub-contracts required"


# ── Citation chip ────────────────────────────────────────────────────────────

def test_css_contains_citation_chip_selector(css_text: str) -> None:
    assert ".drhp-cite" in css_text
    assert "background: #E0A24E" in css_text
    assert "font-size: 0.7em" in css_text
    assert "vertical-align: super" in css_text


# ── Focus ring ───────────────────────────────────────────────────────────────

def test_css_contains_focus_ring_2px_offset(css_text: str) -> None:
    assert re.search(r"outline:\s*2px\s+solid\s+#E0A24E", css_text), \
        "Focus ring outline not found"
    assert re.search(r"outline-offset:\s*2px", css_text), \
        "outline-offset: 2px not found"


# ── Refusal banner amber, not red ────────────────────────────────────────────

def test_css_contains_refusal_banner_amber_not_red(css_text: str) -> None:
    # Refusal banner is AMBER, never destructive red (UI-SPEC §Color — refusal is
    # honest, not punitive). In the Deep Slate DARK palette the amber lives in
    # semantic tokens: a dark amber-tinted surface, the kept amber border #D97706,
    # and light amber text. The invariant guarded here is amber-not-red, unchanged.
    assert re.search(r"--drhp-refusal-border:\s*#D97706", css_text), \
        "Refusal amber border token #D97706 missing"
    assert "border-left: 4px solid var(--drhp-refusal-border)" in css_text, \
        "Refusal banner must use the amber refusal-border token"
    assert "background: var(--drhp-refusal-bg)" in css_text, \
        "Refusal banner background must go through the amber refusal-bg token"
    assert "#B91C1C" not in css_text, \
        "Destructive red #B91C1C must NOT appear in CSS (UI-SPEC §Color)"


# ── Four breakpoints ─────────────────────────────────────────────────────────

def test_css_contains_three_breakpoints(css_text: str) -> None:
    assert "@media (max-width: 374px)" in css_text
    assert "@media (min-width: 375px) and (max-width: 639px)" in css_text
    assert "@media (min-width: 640px) and (max-width: 1023px)" in css_text
    assert "@media (min-width: 1024px)" in css_text


# ── Reduced motion ───────────────────────────────────────────────────────────

def test_css_contains_prefers_reduced_motion(css_text: str) -> None:
    assert "@media (prefers-reduced-motion: reduce)" in css_text


# ── Default Streamlit footer suppression ─────────────────────────────────────

def test_css_hides_default_streamlit_footer(css_text: str) -> None:
    assert '[data-testid="stFooter"]' in css_text
    assert "display: none" in css_text


# ── 44px tap target ──────────────────────────────────────────────────────────

def test_css_contains_44px_touch_target(css_text: str) -> None:
    assert re.search(r"min-width:\s*44px", css_text), "min-width: 44px not found"
    assert re.search(r"min-height:\s*44px", css_text), "min-height: 44px not found"


# ── Idempotency ──────────────────────────────────────────────────────────────

def test_load_global_css_injects_every_run() -> None:
    # The <style> must be returned on EVERY call so it can be re-emitted each
    # script run. Streamlit removes elements not produced by the current run, so
    # a once-only guard dropped the whole stylesheet after the first
    # st.rerun()/st.stop() (e.g. dismissing the first-use modal), leaving the
    # catalogue and subsequent pages unstyled.
    from app.util.css_loader import load_global_css
    ss: dict = {}
    r1 = load_global_css(ss)
    r2 = load_global_css(ss)
    assert r1 is not None, "First call must return CSS string"
    assert r2 is not None, "Every call must return CSS (re-injected each run)"
    assert r1 == r2, "CSS must be identical across runs (stable delta position)"
    assert r1.startswith("<style>") and r1.endswith("</style>")


def test_load_global_css_returns_html_with_style_tag() -> None:
    from app.util.css_loader import load_global_css
    ss: dict = {}
    result = load_global_css(ss)
    assert result is not None
    assert result.startswith("<style>"), f"Expected '<style>' prefix, got: {result[:30]!r}"
    assert result.endswith("</style>"), f"Expected '</style>' suffix, got: {result[-30:]!r}"
