"""
TDD Task 2 — ui/chip.py + ui/expander.py

Tests the citation chip renderer contract (UI-02, T-1-06, D-01, D-03, PITFALL P5, T-1-11).
Wave 0 xfail stub replaced with full implementation tests.
"""
from __future__ import annotations

import re

import pytest

from agent.schemas import Claim, GroundedAnswer, RetrievedChunkRef
from ui.chip import build_chip_html, render_answer_with_chips
from ui.expander import SEBI_PROSPECTUS_URL, render_citation_expanders


# ── Factories ────────────────────────────────────────────────────────────────

def _make_ref(page: int = 5, section: str = "Use of Proceeds") -> RetrievedChunkRef:
    return RetrievedChunkRef(
        chunk_id="chunk_001",
        page_start=page,
        page_end=page + 1,
        section=section,
        verbatim_span="Swiggy plans to use the proceeds for expansion.",
    )


def _make_claim(claim_id: str = "c_4f3a8b", page: int = 5) -> Claim:
    return Claim(
        claim_id=claim_id,
        text="Swiggy plans to use the proceeds for expansion.",
        source_chunk_id="chunk_001",
        drhp_page=page,
        section="Use of Proceeds",
        verbatim_span="Swiggy plans to use the proceeds for expansion.",
        span_offsets=(0, 46),
        sources=[_make_ref(page)],
    )


def _make_answer(prose: str, claims: list[Claim]) -> GroundedAnswer:
    return GroundedAnswer(answer_prose=prose, claims=claims)


# ── XSS escape (Wave 0 xfail → GREEN) ───────────────────────────────────────

def test_renderer_emits_sup_chip_html_and_escapes_xss() -> None:
    """T-1-06: prose containing <script> is escaped; chip HTML is correct."""
    claim = _make_claim()
    prose = "The DRHP says X.{{c_4f3a8b}} <script>alert(1)</script> Y.{{c_4f3a8b}}"
    answer = _make_answer(prose, [claim])
    rendered, chip_map = render_answer_with_chips(answer)

    # chip HTML present
    assert 'class="drhp-cite"' in rendered
    assert 'data-claim-id="c_4f3a8b"' in rendered
    assert 'tabindex="0"' in rendered
    assert 'role="button"' in rendered

    # XSS escaped
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered, \
        "XSS attempt must be escaped"
    assert "<script>alert(1)</script>" not in rendered, \
        "Raw <script> must not appear in output"


# ── D-03 cluster dedupe ──────────────────────────────────────────────────────

def test_chip_cluster_dedupe_per_uispec_d03() -> None:
    """Three consecutive citations of same claim_id → ONE chip at last position."""
    claim = _make_claim()
    prose = "X.{{c_4f3a8b}} Y.{{c_4f3a8b}} Z.{{c_4f3a8b}}"
    answer = _make_answer(prose, [claim])
    rendered, chip_map = render_answer_with_chips(answer)

    # Only ONE chip in output
    chip_count = rendered.count('class="drhp-cite"')
    assert chip_count == 1, f"Expected 1 chip after dedup, got {chip_count}"
    # The underlying claim_id is still in the map
    assert "c_4f3a8b" in chip_map


# ── D-01 numbering resets per answer ─────────────────────────────────────────

def test_chip_numbering_resets_per_answer() -> None:
    """Chip numbers start at [1] for each fresh render_answer_with_chips call."""
    claim = _make_claim()
    prose = "A.{{c_4f3a8b}}"
    answer = _make_answer(prose, [claim])

    _, chip_map1 = render_answer_with_chips(answer)
    _, chip_map2 = render_answer_with_chips(answer)

    assert chip_map1["c_4f3a8b"] == 1
    assert chip_map2["c_4f3a8b"] == 1


# ── Distinct claim_ids get sequential numbers ─────────────────────────────────

def test_distinct_claim_ids_get_sequential_numbers() -> None:
    """c_aaaaaa→1, c_bbbbbb→2; second c_aaaaaa reuses 1."""
    claim_a = _make_claim("c_aaaaaa")
    claim_b = _make_claim("c_bbbbbb")
    prose = "A.{{c_aaaaaa}} B.{{c_bbbbbb}} C.{{c_aaaaaa}}"
    answer = _make_answer(prose, [claim_a, claim_b])
    rendered, chip_map = render_answer_with_chips(answer)

    assert chip_map["c_aaaaaa"] == 1
    assert chip_map["c_bbbbbb"] == 2
    # c_aaaaaa appears twice (with c_bbbbbb between them, so NOT contiguous cluster)
    assert rendered.count("[1]") == 2
    assert rendered.count("[2]") == 1


# ── aria-describedby ──────────────────────────────────────────────────────────

def test_chip_html_contains_aria_describedby() -> None:
    """Every chip must have aria-describedby='cite-N-source'."""
    chip = build_chip_html("c_4f3a8b", 3)
    assert 'aria-describedby="cite-3-source"' in chip


# ── Period before chip ────────────────────────────────────────────────────────

def test_period_before_chip_per_uispec() -> None:
    """Renderer preserves punctuation before placeholder; does not relocate it."""
    claim = _make_claim()
    prose = "X is true.{{c_4f3a8b}}"
    answer = _make_answer(prose, [claim])
    rendered, _ = render_answer_with_chips(answer)

    # The period must come before the chip sup tag
    period_pos = rendered.index(".")
    chip_pos = rendered.index("<sup")
    assert period_pos < chip_pos, "Period must be before the chip <sup>"


# ── Unknown placeholder falls through unchanged ───────────────────────────────

def test_unmatched_placeholder_falls_through_unchanged(caplog) -> None:
    """Unknown {{claim_id}} not in claims → left literal, warning logged."""
    import logging
    claim = _make_claim()
    prose = "X.{{c_unknown}} Y."
    answer = _make_answer(prose, [claim])

    with caplog.at_level(logging.WARNING, logger="ui.chip"):
        rendered, _ = render_answer_with_chips(answer)

    assert "{{c_unknown}}" in rendered, "Unknown placeholder must remain in output"
    assert 'class="drhp-cite"' not in rendered or "c_unknown" not in rendered
    assert any("c_unknown" in r.message for r in caplog.records), \
        "Warning must be logged for unknown placeholder"


# ── render_citation_expanders ─────────────────────────────────────────────────

def test_render_citation_expanders_pairs_with_chip_numbers() -> None:
    """render_citation_expanders returns one dict per unique claim_id, ordered by chip_n."""
    claim = _make_claim()
    prose = "A.{{c_4f3a8b}}"
    answer = _make_answer(prose, [claim])
    _, chip_map = render_answer_with_chips(answer)
    expanders = render_citation_expanders(answer, chip_map)

    assert len(expanders) == 1
    exp = expanders[0]
    assert exp["chip_n"] == 1
    assert exp["claim_id"] == "c_4f3a8b"
    assert "label" in exp
    assert "snippet" in exp
    assert "source_url" in exp
    assert "page_start" in exp
    assert "section" in exp
    assert "metadata_footer" in exp
    assert exp["source_url"].startswith(SEBI_PROSPECTUS_URL)
    assert "#page=" in exp["source_url"]


# ── claim_id round-trip ───────────────────────────────────────────────────────

def test_round_trip_claim_id_through_renderer() -> None:
    """claim_id round-trips byte-for-byte from Claim → chip data-claim-id (T-1-11)."""
    claim_id = "c_4f3a8b"
    claim = _make_claim(claim_id)
    prose = f"Fact.{{{{{claim_id}}}}}"
    answer = _make_answer(prose, [claim])
    rendered, _ = render_answer_with_chips(answer)

    # Parse data-claim-id from rendered HTML
    m = re.search(r'data-claim-id="([^"]+)"', rendered)
    assert m is not None, "data-claim-id attribute not found in rendered HTML"
    assert m.group(1) == claim_id, \
        f"claim_id drifted: expected {claim_id!r}, got {m.group(1)!r}"
