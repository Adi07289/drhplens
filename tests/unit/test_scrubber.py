"""
TDD Wave 1 — compliance/banned_tokens.py + compliance/scrubber.py.

Tests the deterministic banned-token scrubber (TRUST-02 / PITFALL 5 prevention).

Design notes on matched_token values:
  The scrubber uses morphological STEMS for matching (not full word forms) because
  Python literal matching does not support dropping the silent 'e' in "subscribe" ->
  "subscribing". The stems are defined in compliance/banned_tokens.py:
    subscri    -> subscribe, subscribed, subscribing, subscription
    accumulat  -> accumulate, accumulated, accumulating
  Multi-word phrase matches return the full phrase as matched_token:
    "fair value", "target price", "book profits"

All tests verify ScrubResult.passed (bool) and ScrubResult.matched_token (str | None).
"""
from __future__ import annotations

import re

import pytest

from compliance.banned_tokens import BANNED_TOKEN_PATTERN, BANNED_TOKENS
from compliance.scrubber import ScrubResult, scrub


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_blocked(text: str, expected_root: str) -> None:
    """Assert scrub(text) is blocked and matched_token == expected_root."""
    r = scrub(text)
    assert r.passed is False, f"Expected blocked for {text!r}, got passed=True"
    assert r.matched_token == expected_root, (
        f"Expected matched_token={expected_root!r} for {text!r}, got {r.matched_token!r}"
    )
    assert r.match is not None


def _assert_passes(text: str) -> None:
    """Assert scrub(text) passes (no banned token)."""
    r = scrub(text)
    assert r.passed is True, f"Expected passed for {text!r}, got blocked on {r.matched_token!r}"
    assert r.match is None
    assert r.matched_token is None


# ---------------------------------------------------------------------------
# ScrubResult dataclass shape
# ---------------------------------------------------------------------------

def test_scrub_result_dataclass_shape() -> None:
    """ScrubResult has passed: bool, match: str | None, matched_token: str | None."""
    r1 = ScrubResult(passed=True, match=None, matched_token=None)
    assert r1.passed is True
    assert r1.match is None
    assert r1.matched_token is None

    r2 = ScrubResult(passed=False, match="recommended", matched_token="recommend")
    assert r2.passed is False
    assert r2.match == "recommended"
    assert r2.matched_token == "recommend"


# ---------------------------------------------------------------------------
# BANNED_TOKENS shape
# ---------------------------------------------------------------------------

def test_banned_tokens_tuple_has_minimum_length() -> None:
    """BANNED_TOKENS must have >= 16 canonical token strings."""
    assert len(BANNED_TOKENS) >= 16, f"Expected >= 16 tokens, got {len(BANNED_TOKENS)}"


def test_banned_token_pattern_flags() -> None:
    """BANNED_TOKEN_PATTERN must have IGNORECASE and UNICODE flags."""
    assert BANNED_TOKEN_PATTERN.flags & re.IGNORECASE, "Missing re.IGNORECASE"
    assert BANNED_TOKEN_PATTERN.flags & re.UNICODE, "Missing re.UNICODE"


# ---------------------------------------------------------------------------
# UI-SPEC L-5 locked tokens — base forms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,root", [
    ("you should subscribe to this IPO", "subscri"),
    ("we recommend caution", "recommend"),
    ("buy this stock", "buy"),
    ("sell now", "sell"),
    ("avoid this", "avoid"),
    ("the target price is X", "target price"),
    ("fair value estimate", "fair value"),
    ("overvalued by 20%", "overvalued"),
    ("undervalued stock", "undervalued"),
])
def test_base_locked_token_blocked(text: str, root: str) -> None:
    """Every UI-SPEC L-5 locked token (base form) triggers the scrubber."""
    _assert_blocked(text, root)


# ---------------------------------------------------------------------------
# Morphological variants — subscribe family
# ---------------------------------------------------------------------------

def test_subscribe_blocked() -> None:
    """'subscribe' in context is blocked."""
    _assert_blocked("you should subscribe to this IPO", "subscri")


def test_subscribed_blocked() -> None:
    """'subscribed' is blocked (PITFALL 5 morphological variant)."""
    _assert_blocked("we subscribed last week", "subscri")


def test_subscribing_blocked() -> None:
    """'subscribing' is blocked (present participle morphological variant)."""
    _assert_blocked("subscribing makes sense here", "subscri")


def test_subscription_blocked() -> None:
    """'subscription' is blocked (noun form morphological variant)."""
    _assert_blocked("subscription required to participate", "subscri")


# ---------------------------------------------------------------------------
# Morphological variants — recommend family
# ---------------------------------------------------------------------------

def test_recommend_blocked() -> None:
    _assert_blocked("we recommend caution", "recommend")


def test_recommended_blocked() -> None:
    _assert_blocked("the analyst recommended the stock", "recommend")


def test_recommending_blocked() -> None:
    _assert_blocked("we are recommending this issue", "recommend")


def test_recommendation_blocked() -> None:
    _assert_blocked("our recommendation is to wait", "recommend")


# ---------------------------------------------------------------------------
# Morphological variants — buy/sell/avoid
# ---------------------------------------------------------------------------

def test_buy_blocked() -> None:
    _assert_blocked("buy this stock", "buy")


def test_buying_blocked() -> None:
    _assert_blocked("buying makes sense here", "buy")


def test_sell_blocked() -> None:
    _assert_blocked("sell now", "sell")


def test_selling_blocked() -> None:
    _assert_blocked("selling now is prudent", "sell")


def test_avoid_blocked() -> None:
    _assert_blocked("avoid this IPO", "avoid")


def test_avoided_blocked() -> None:
    _assert_blocked("investors avoided the issue", "avoid")


def test_avoiding_blocked() -> None:
    _assert_blocked("avoiding this is wise", "avoid")


# ---------------------------------------------------------------------------
# Multi-word tokens
# ---------------------------------------------------------------------------

def test_target_blocked() -> None:
    _assert_blocked("target is 200", "target")


def test_target_price_blocked() -> None:
    """'target price' as a phrase triggers the phrase rule before 'target'."""
    _assert_blocked("target price is high", "target price")


def test_fair_value_blocked() -> None:
    _assert_blocked("the fair value estimate is X", "fair value")


def test_book_profits_blocked() -> None:
    _assert_blocked("book profits now", "book profits")


# ---------------------------------------------------------------------------
# Planner-discretion extensions
# ---------------------------------------------------------------------------

def test_accumulate_blocked() -> None:
    _assert_blocked("accumulate position", "accumulat")


def test_accumulating_blocked() -> None:
    _assert_blocked("accumulating more shares", "accumulat")


def test_outperform_blocked() -> None:
    _assert_blocked("outperform rating assigned", "outperform")


def test_underperform_blocked() -> None:
    _assert_blocked("underperform classification", "underperform")


def test_bullish_blocked() -> None:
    _assert_blocked("bullish outlook on Swiggy", "bullish")


def test_bearish_blocked() -> None:
    _assert_blocked("bearish sentiment prevails", "bearish")


# ---------------------------------------------------------------------------
# Passes — neutral DRHP language
# ---------------------------------------------------------------------------

def test_neutral_text_passes() -> None:
    """Pure DRHP informational text passes the scrubber."""
    _assert_passes("The DRHP discloses a promoter holding of 31.4%.")


def test_financial_fact_passes() -> None:
    """A factual statement with no banned tokens passes."""
    _assert_passes("The company reported revenue of ₹3,288 crore in FY24.")


def test_risk_factor_passes() -> None:
    """A risk-factor statement passes the scrubber."""
    _assert_passes(
        "The company has incurred net losses since inception and may "
        "not achieve profitability in the near term."
    )


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------

def test_case_insensitive_buy() -> None:
    """Uppercase 'BUY' is blocked."""
    _assert_blocked("BUY THIS", "buy")


def test_case_insensitive_subscribe() -> None:
    """Mixed-case 'Subscribe' is blocked."""
    _assert_blocked("Subscribe to the IPO", "subscri")


def test_case_insensitive_recommend() -> None:
    """All-caps 'RECOMMEND' is blocked."""
    _assert_blocked("RECOMMEND caution", "recommend")


# ---------------------------------------------------------------------------
# Word boundary — no false positives on unrelated words
# ---------------------------------------------------------------------------

def test_word_boundary_no_false_positive_syllabus() -> None:
    """'syllabus' does NOT contain a word-boundary-anchored banned token."""
    _assert_passes("syllabus")


def test_word_boundary_no_false_positive_resell() -> None:
    """'resell' — the 'sell' stem fires at word boundary 'sell' within 'resell'?
    Actually 'sell' IS a word in 'resell' context when preceded by non-\\w... wait.
    'resell' = r-e-s-e-l-l — no word boundary before 'sell' within the word,
    so \\b(sell)\\w*\\b does NOT match 'resell' as a whole. Verify:
    """
    # The word boundary \\b before 'sell' requires a non-\\w char before it.
    # In 'resell', 'e' before 'sell' is \\w, so \\b does NOT fire.
    _assert_passes("resell items from portfolio")


def test_unsubscribed_user_list_passes() -> None:
    """'unsubscribed' — the 'u' before 'subscri' prevents the word boundary from firing.
    This is the CORRECT behavior: 'unsubscribed users' is a legitimate non-financial term.
    The stem 'subscri' requires \\b at the start; 'un' before 'subscri' means no boundary.
    """
    _assert_passes("the unsubscribed user list")


# ---------------------------------------------------------------------------
# Unicode: homoglyph does NOT fire (documented behavior, not a bug)
# ---------------------------------------------------------------------------

def test_cyrillic_homoglyph_does_not_fire() -> None:
    """Cyrillic 's' in 'ѕubscribe' is NOT matched by the Latin-character regex.
    This is documented behavior: we do not defend against homoglyph attacks
    at the scrubber layer (see compliance/banned_tokens.py module docstring §6).
    """
    # U+0455 is the Cyrillic 'dze' which looks like 's'
    cyrillic_s = "ѕ"
    _assert_passes(cyrillic_s + "ubscribe to this IPO")


# ---------------------------------------------------------------------------
# Multiple violations — first-match only
# ---------------------------------------------------------------------------

def test_multiple_violations_returns_first() -> None:
    """When multiple banned tokens appear, scrub() returns the first match only."""
    r = scrub("buy and sell today")
    assert r.passed is False
    # Either "buy" or "sell" fired — both are blocked; first-match returned
    assert r.matched_token in ("buy", "sell")
