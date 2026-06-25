"""
Unit test stub — the "show your work" methodology pane (METHOD-01): renders from
cached per-claim data (no live LLM/Qdrant call), and the module imports no LLM or
Qdrant client (the inspect.getsource / AST substring check mirroring
test_cite_check.test_no_llm_judge_fallback).

Requirement: METHOD-01. Wave 0 stub — Plan 06 implements ui/methodology_pane.py.
Function names are LOCKED; Plan 06 fills the bodies.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Plan 06 implements ui/methodology_pane.py")


def test_pane_renders_from_cache() -> None:
    """The pane builds its content (query / chunks+scores / prompt / sources /
    eval scores) from cached RedFlagRecord + committed eval reports, no live call."""
    raise NotImplementedError


def test_no_llm_or_qdrant_import() -> None:
    """ui/methodology_pane.py must not import any LLM or Qdrant client
    (Pitfall 5: pane is pure render over cached data)."""
    raise NotImplementedError
