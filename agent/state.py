"""
GraphState TypedDict — the locked LangGraph state for DRHPLens Phase 1.

Every key listed here is consumed by at least one LangGraph node in Wave 3.
Do NOT rename or remove keys without updating every graph node that reads them.
The graph conditional edges (in agent/graph.py) branch on:
  - gate1_passed: bool
  - scrub_passed: bool
  - regenerate_attempts: int (< 1 → retry generate; >= 1 → refuse)
  - all_claims_grounded: bool
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

# Import schemas for runtime annotation resolution (LangGraph inspects annotations at build time)
from agent.schemas import GroundedAnswer, RefusalResponse


class GraphState(TypedDict):
    """LangGraph state dict threaded through every node in the agent graph.

    Field contracts (locked for Wave 3 consumption):
    - question: raw user question from st.chat_input
    - retrieved_chunks: raw Qdrant payload dicts from the retrieve node;
      converted to RetrievedChunkRef at cite-check time
    - reranked_top_k: subset of retrieved_chunks after bge-reranker-v2-m3
    - gate1_passed: True iff max reranker score >= threshold (D-05 Gate 1)
    - gate1_max_score: the highest reranker score seen in this query; used
      for logging and threshold-tuning during Phase 1 eval
    - sub_questions: list of decomposed sub-questions from the decompose node (D-06)
    - grounded_answer: Instructor-validated GroundedAnswer or None if not yet
      generated / if generation was refused
    - scrub_passed: True iff the banned-token scrubber cleared the answer (D-09)
    - regenerate_attempts: counter for the hard-block-and-regenerate loop;
      Wave 3 graph uses `regenerate_attempts < 1` to gate a single retry
    - all_claims_grounded: True iff cite-check validated every claim (D-05 Gate 2)
    - cite_check_failures: per-claim failure reasons from the cite-check node
    - refusal: populated by refuse_with_reformulation node; None otherwise
    """

    question: str
    retrieved_chunks: list[dict]
    reranked_top_k: list[dict]
    gate1_passed: bool
    gate1_max_score: float
    sub_questions: list[str]
    grounded_answer: GroundedAnswer | None
    scrub_passed: bool
    regenerate_attempts: int
    all_claims_grounded: bool
    cite_check_failures: list[str]
    refusal: RefusalResponse | None
