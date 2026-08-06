"""
SupervisorState TypedDict — the bounded multi-tool supervisor's state (Phase 6.3, D-06/D-02).

`SupervisorState` is a strict SUPERSET of `agent.state.GraphState`: it EXTENDS
(subclasses) GraphState so every existing key keeps ONE fixed meaning, and it ADDS
only the disjoint supervisor-only keys the P8 loop guard + fusion need. It never
redefines an inherited key.

Pitfall #1 (state-key collision): the supervisor embeds the existing 10-node
DRHP-RAG graph as a sub-agent (D-02). That subgraph reads/writes the GraphState
keys (`question`, `drhp_id`, `grounded_answer`, `refusal`, `regenerate_attempts`,
…) with one fixed meaning. If the supervisor reused any of those keys with a
DIFFERENT meaning, the subgraph and supervisor would silently clobber each other.
Extending GraphState (a superset) keeps the shared contract intact; the six new
keys below are deliberately disjoint from every GraphState key.

The P8 bound constants that read `hops` / `tool_calls` / `started_at` live in
agent/policies.py (MAX_SUPERVISOR_HOPS, MAX_TOOL_CALLS, WALL_CLOCK_S) — this
module carries only the state shape, no logic.
"""
from __future__ import annotations

from agent.state import GraphState


class SupervisorState(GraphState):
    """Supervisor state — GraphState superset for the bounded multi-tool agent.

    Inherits every GraphState key unchanged (subgraph contract, Pitfall #1) and
    ADDS only these disjoint supervisor-only keys:

    - hops: supervisor routing-hop counter; the deterministic `route()` halts to
      synthesis when hops > MAX_SUPERVISOR_HOPS (D-06, the real P8 guard).
    - tool_calls: total tool invocations this run; `route()` halts when
      tool_calls >= MAX_TOOL_CALLS (D-06), bounding fan-in to synthesis.
    - tool_plan: the clamped, allow-listed tool set the classify hop proposed
      (D-05); tool nodes pop themselves off this plan as they execute.
    - tool_results: provenance-tagged structured records each executed tool
      appended (a forecast band, a peer row set, a red-flag table) — the fusion
      input, never raw retrieval.
    - started_at: monotonic/epoch start time for the WALL_CLOCK_S backstop (D-06).
    - is_partial: True iff the run returned an honest labelled partial (D-08) —
      a single-tool abstain/error or a hard budget-trip; never a fabrication.
    """

    hops: int
    tool_calls: int
    tool_plan: list[str]
    tool_results: list[dict]
    started_at: float
    is_partial: bool
