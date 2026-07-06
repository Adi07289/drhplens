"""
Unit test — ui/format_inr.py, the ONE shared Indian rupee formatter (D4-07, UI-04).

Requirement: UI-04. Threat: T-04-02-INJ (accept — output is a formatted numeric
string with no user-controlled text; see 04-02-PLAN.md threat register).

Pins the RESEARCH §Code Examples test-case table exactly, including the A8
decision to apply Indian digit grouping (last three digits, then groups of two)
to the integer part of scaled lakh/crore values too (`₹1,247 crore`).

Pure-function assert style mirrors tests/unit/test_catalogue.py.
"""
from __future__ import annotations

import pytest

from ui.format_inr import format_inr


# --- Sub-lakh: Indian digit grouping (NOT Western) -------------------------

def test_sub_lakh_indian_grouping() -> None:
    """45,600 groups Indian-style (identical to Western at 5 digits, but via
    the Indian grouper — the regression guard is the six-digit case below)."""
    assert format_inr(45600) == "₹45,600"


def test_six_digit_boundary_is_lakh_not_western() -> None:
    """A six-digit rupee amount auto-scales to lakh — the FLAG-FORMAT bug fix.
    Western grouping would have rendered ₹1,00,000 as ₹100,000; here it is ₹1 lakh."""
    assert format_inr(100000) == "₹1 lakh"


# --- Lakh scaling ----------------------------------------------------------

def test_lakh_exact_one() -> None:
    assert format_inr(100000) == "₹1 lakh"


def test_lakh_one_decimal_trimmed() -> None:
    """1250000 / 1e5 = 12.5 — trailing zero trimmed (₹12.5 lakh, not ₹12.50 lakh)."""
    assert format_inr(1250000) == "₹12.5 lakh"


def test_lakh_two_decimal_rounding() -> None:
    """1234567 / 1e5 = 12.34567 → rounds to 2 dp → ₹12.35 lakh (PLAN behavior)."""
    assert format_inr(1234567) == "₹12.35 lakh"


# --- Crore scaling ---------------------------------------------------------

def test_crore_two_decimals() -> None:
    """124700000 / 1e7 = 12.47 → ₹12.47 crore."""
    assert format_inr(124700000) == "₹12.47 crore"


def test_crore_integer_part_indian_grouped_A8() -> None:
    """A8: a value ≥ 1e9 scales to crore with Indian grouping on the integer
    part. 1247 crore = 1.247e10 → ₹1,247 crore (NOT ₹1247 crore)."""
    assert format_inr(12470000000) == "₹1,247 crore"


def test_crore_large_no_double_scale() -> None:
    """A ₹11,327 crore issue (in rupees) renders ₹11,327 crore — never
    re-scaled into ₹1.13 lakh crore (double-scaling guard)."""
    assert format_inr(113270000000) == "₹11,327 crore"


def test_crore_exact_one() -> None:
    assert format_inr(10000000) == "₹1 crore"


def test_crore_trailing_zeros_trimmed() -> None:
    """₹1,247 crore, never ₹1247.00 crore."""
    assert format_inr(12470000000) == "₹1,247 crore"


# --- Arithmetic sanity: 1 crore = 100 lakh (no off-by-10×) -----------------

def test_one_crore_equals_hundred_lakh_boundary() -> None:
    """9999999 (< 1e7) is still lakh; 10000000 (= 1e7) flips to crore."""
    assert format_inr(9999999) == "₹100 lakh"
    assert format_inr(10000000) == "₹1 crore"


# --- Sentinels + negatives -------------------------------------------------

def test_none_renders_em_dash() -> None:
    assert format_inr(None) == "—"


def test_negative_wrapped_in_parentheses_no_sign_token() -> None:
    """Negatives render in parentheses in the same (inherited, no-red)
    convention — no minus sign, no colour token."""
    assert format_inr(-1234) == "(₹1,234)"


def test_negative_lakh_in_parentheses() -> None:
    assert format_inr(-1250000) == "(₹12.5 lakh)"


# --- Purity ----------------------------------------------------------------

def test_returns_string_in_every_branch() -> None:
    for v in (None, 0, -1234, 45600, 100000, 1250000, 124700000, 12470000000):
        assert isinstance(format_inr(v), str)


def test_zero_renders_grouped_rupees() -> None:
    assert format_inr(0) == "₹0"


@pytest.mark.parametrize(
    "amount,expected",
    [
        (100000, "₹1 lakh"),
        (1250000, "₹12.5 lakh"),
        (124700000, "₹12.47 crore"),
        (45600, "₹45,600"),
        (1234567, "₹12.35 lakh"),
        (None, "—"),
        (-1234, "(₹1,234)"),
    ],
)
def test_research_case_table(amount, expected) -> None:
    """The RESEARCH §Code Examples test-case table, pinned exactly."""
    assert format_inr(amount) == expected
