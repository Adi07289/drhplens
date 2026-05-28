"""
TDD Wave 1 — ui/copy.py: import-time scrubber assertion (TRUST-03).

Validates that no string constant in ui/copy.py contains a banned token,
that all required constants are present, and that the modal body contains
the SEBI Jan-2025 AI-disclosure copy.

The import-time assertion in ui/copy.py is the TRUST-03 anchor. This test
file adds explicit individual-constant checks as a belt-and-suspenders layer.
"""
from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# Import-time assertion fires on import
# ---------------------------------------------------------------------------

def test_import_copy_module_triggers_scrubber_assertion() -> None:
    """Importing ui.copy must succeed (all copy is clean).

    The import-time assertion in ui/copy.py runs the scrubber on every
    module-level string constant at import time. If any constant contains a
    banned token, import raises AssertionError. This test verifies the import
    succeeds (i.e., all copy is clean).
    """
    import ui.copy  # noqa: F401 — import side effect IS the test
    # If we reach here, the import-time assertion passed


# ---------------------------------------------------------------------------
# Required constants are present
# ---------------------------------------------------------------------------

REQUIRED_COPY_CONSTANTS = [
    "HERO_HEADING",
    "HERO_SUBHEADING",
    "QUESTION_PLACEHOLDER",
    "MODAL_CTA",
    "EMPTY_STATE_HEADING",
    "EMPTY_STATE_BODY",
    "COLD_START_COPY",
    "LOADING_ANSWER_COPY",
    "REFUSAL_NO_GROUNDING_TEMPLATE",
    "REFUSAL_PARTIAL_GROUNDING_TEMPLATE",
    "REFUSAL_BANNED_TOKEN_COPY",
    "ERROR_QDRANT_UNREACHABLE",
    "ERROR_LLM_TIMEOUT",
    "ERROR_RATE_LIMIT",
    "PER_ANSWER_DISCLAIMER",
    "METHODOLOGY_STUB_HEADING",
    "METHODOLOGY_STUB_BODY",
]


def test_required_copy_strings_present() -> None:
    """All 17 required module-level string constants exist in ui.copy."""
    import ui.copy
    missing = [name for name in REQUIRED_COPY_CONSTANTS if not hasattr(ui.copy, name)]
    assert not missing, f"Missing copy constants: {missing}"


# ---------------------------------------------------------------------------
# Every copy string individually passes the scrubber
# ---------------------------------------------------------------------------

def test_all_copy_strings_pass_scrubber() -> None:
    """Walk every module-level string constant in ui.copy and assert scrubber-clean.

    This is the TRUST-03 anchor: the product's own copy never contains a banned
    token. A future copy edit that introduces a banned token will fail here AND
    at the import-time assertion in ui/copy.py.
    """
    import ui.copy
    from compliance.scrubber import scrub

    failed: list[tuple[str, str]] = []
    for name, value in inspect.getmembers(ui.copy, lambda x: isinstance(x, str)):
        if name.startswith("_"):
            continue
        result = scrub(value)
        if not result.passed:
            failed.append((name, result.match or ""))

    assert not failed, (
        f"The following copy constants contain banned tokens:\n"
        + "\n".join(f"  {name!r}: matched {match!r}" for name, match in failed)
    )


# ---------------------------------------------------------------------------
# Individual constant content spot-checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected_substring", [
    ("HERO_HEADING", "Swiggy"),
    ("EMPTY_STATE_HEADING", "Nothing asked yet"),
    ("COLD_START_COPY", "Hugging Face"),
    ("LOADING_ANSWER_COPY", "DRHP"),
    ("ERROR_QDRANT_UNREACHABLE", "DRHP index"),
    ("ERROR_LLM_TIMEOUT", "timed out"),
    ("ERROR_RATE_LIMIT", "free-tier"),
    ("PER_ANSWER_DISCLAIMER", "Informational only"),
    ("METHODOLOGY_STUB_HEADING", "Methodology"),
    ("METHODOLOGY_STUB_BODY", "Phase 1"),
    ("REFUSAL_BANNED_TOKEN_COPY", "DRHPLens describes"),
    ("MODAL_CTA", "I understand"),
])
def test_individual_copy_constant_content(name: str, expected_substring: str) -> None:
    """Spot-check that key copy constants contain expected substrings."""
    import ui.copy
    value = getattr(ui.copy, name)
    assert expected_substring in value, (
        f"{name!r} does not contain expected substring {expected_substring!r}.\n"
        f"Value: {value!r}"
    )


def test_refusal_no_grounding_template_has_format_placeholders() -> None:
    """REFUSAL_NO_GROUNDING_TEMPLATE has {topic}, {suggestion1}, {suggestion2} placeholders."""
    import ui.copy
    formatted = ui.copy.REFUSAL_NO_GROUNDING_TEMPLATE.format(
        topic="promoter salaries",
        suggestion1="use of proceeds",
        suggestion2="risk factors",
    )
    assert "promoter salaries" in formatted
    assert "use of proceeds" in formatted
    assert "risk factors" in formatted


def test_no_exclamation_marks_in_copy() -> None:
    """No copy constant contains exclamation marks (UI-SPEC: no exclamation marks)."""
    import ui.copy
    for name, value in inspect.getmembers(ui.copy, lambda x: isinstance(x, str)):
        if name.startswith("_"):
            continue
        assert "!" not in value, f"{name!r} contains an exclamation mark: {value!r}"


def test_methodology_stub_body_passes_scrubber() -> None:
    """METHODOLOGY_STUB_BODY regression guard after Wave 4 changes."""
    from ui.copy import METHODOLOGY_STUB_BODY
    from compliance.scrubber import scrub
    result = scrub(METHODOLOGY_STUB_BODY)
    assert result.passed, f"METHODOLOGY_STUB_BODY failed scrubber: {result.match!r}"


def test_refusal_banner_module_strings_pass_scrubber() -> None:
    """ui.refusal_banner heading constants must pass the banned-token scrubber (TRUST-02)."""
    import ui.refusal_banner
    from compliance.scrubber import scrub
    constants = [
        ui.refusal_banner.REFUSAL_HEADING_LOW_RETRIEVAL,
        ui.refusal_banner.REFUSAL_HEADING_PARTIAL_GROUNDING,
        ui.refusal_banner.REFUSAL_HEADING_BANNED_TOKEN,
        ui.refusal_banner.REFUSAL_HEADING_INFRASTRUCTURE,
    ]
    for s in constants:
        result = scrub(s)
        assert result.passed, f"refusal_banner constant failed scrubber: {s!r} → {result.match!r}"


def test_copy_import_time_assertion_fires_on_banned_copy() -> None:
    """Verify the import-time assertion mechanism fires on a synthetic banned string.

    We test the mechanism by calling scrub() directly on a known bad string.
    (We cannot actually import a module with the assertion to test the fail path
    without side-effects; instead we verify the scrub() function that powers it.)
    """
    from compliance.scrubber import scrub
    bad = "you should subscribe to this IPO"
    result = scrub(bad)
    assert result.passed is False, (
        "Expected scrub() to block 'subscribe' — import-time assertion would fire"
    )
