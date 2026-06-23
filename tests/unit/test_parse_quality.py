"""
Unit test stub — a DRHP that parses to < N sections / fails table extraction is
flagged, not silently ingested (Pitfall P14).

Requirement: (P14). Threat: none (data-quality robustness concern).
Secure behavior: parse-quality gate flags fallback/garbage parses; flagged IPOs
are excluded from catalogue.json rather than silently shipped with bad data.

Wave 0 stub — Wave 2 implements (02-VALIDATION.md row "2-parse-quality-gate").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 2 — not yet implemented", strict=False)
def test_low_section_count_parse_flagged_as_fallback() -> None:
    raise NotImplementedError
