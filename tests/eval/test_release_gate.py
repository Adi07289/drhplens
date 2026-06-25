"""
Eval test stub — the numeric-faithfulness release gate LOGIC (D3-12), unit-tested
offline on a synthetic result: below NUMERIC_FAITHFULNESS_GATE (0.95) exits
non-zero; at/above passes. Enforcement over discipline — the gate physically
refuses deploy.

Requirement: EVAL-03. Wave 0 stub — Plan 05 implements scripts/release_gate.py.
Function names are LOCKED; Plan 05 fills the bodies. Offline fixture test (no live
infra), so it skips on the implementing plan, not on --run-eval.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Plan 05 implements scripts/release_gate.py")


def test_gate_exits_nonzero_below_threshold() -> None:
    """A synthetic numeric_faithfulness of 0.94 makes the gate exit non-zero."""
    raise NotImplementedError


def test_gate_passes_at_or_above_threshold() -> None:
    """A synthetic numeric_faithfulness of 0.96 makes the gate pass (exit 0)."""
    raise NotImplementedError
