"""
Stub: agent/nodes/decompose.py — multi-part question decomposer (D-06).

Validates that:
- A compound question ("What is the issue size and use of proceeds?") splits into 2 sub-questions
- Sub-question count is bounded (max 4 per 01-RESEARCH.md Open Question 4)
- Single-part questions pass through as a 1-element list
- Sub-question_addressed / sub_question_unaddressed are carried through GroundedAnswer

Wave 3 owns this implementation (RAG-01; D-06 multi-part Q decomposition).
"""
from __future__ import annotations

import pytest

pytest.importorskip("agent.nodes.decompose", reason="agent/nodes/decompose.py ships in Wave 3")


@pytest.mark.xfail(reason="Wave 3 owns this — implements agent/nodes/decompose.py", strict=False)
def test_multipart_question_splits_into_subquestions() -> None:
    """A compound question with 'and' must split into >= 2 sub-questions (capped at 4)."""
    assert False, "Wave 3 must implement: call decompose.run with compound question, assert sub_questions >= 2"
