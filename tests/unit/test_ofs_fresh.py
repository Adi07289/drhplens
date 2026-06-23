"""
Unit test stub — OFS-vs-fresh % computed from use-of-proceeds; foregrounded;
neutral (no green/red) (no threat).

Requirement: SNAP-06. Threat: none (honesty-first / no-perf-badge UI invariant,
not a STRIDE threat).
Secure behavior: the offer-for-sale vs fresh-issue split is computed from the
use-of-proceeds snapshot field and rendered neutrally (D2-06) — no
winner/loser color coding.

Wave 0 stub — Wave 3 implements (02-VALIDATION.md row "2-ofs-fresh-split").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 3 — not yet implemented", strict=False)
def test_ofs_fresh_split_computed_neutrally() -> None:
    raise NotImplementedError
