"""Contract tests for Phase 6.3 Plan 01 — P8 bound constants + SupervisorState superset.

These tests lock two invariants introduced by 06.3-01:

  1. **D-06** — the five P8 loop-safety bound constants exist in ``agent/policies.py``
     as the single-source control surface, each with the documented type/value.
  2. **Pitfall #1** — ``SupervisorState`` is a strict SUPERSET of ``GraphState``: it
     inherits every GraphState key with the SAME annotation and ADDS only the six
     disjoint supervisor-only keys. No inherited key may be silently redefined — a
     redefinition would clobber the embedded DRHP-RAG subgraph's fixed state contract.
"""
from __future__ import annotations

from agent import policies
from agent.state import GraphState
from agent.supervisor_state import SupervisorState

# The supervisor-only keys the superset adds on top of GraphState (Pitfall #1).
# 06.3-01 landed the first six P8-loop keys; 06.3-05 added the two `synthesize`
# OUTPUT channels (`fused_answer` + `disclaimer`) — LangGraph only propagates
# DECLARED channels, so the terminal node's fused answer + post-generation disclaimer
# must be declared here to survive to the final state. Both remain disjoint from
# GraphState and never redefine an inherited key (the superset invariant holds).
SUPERVISOR_ONLY_KEYS = {
    "hops",
    "tool_calls",
    "tool_plan",
    "tool_results",
    "started_at",
    "is_partial",
    "fused_answer",
    "disclaimer",
}


def _ann_str(annotation) -> str:
    """Normalize a TypedDict annotation to its source string.

    Under ``from __future__ import annotations`` the TypedDict metaclass stores
    OWN keys as ``typing.ForwardRef('int')`` while INHERITED keys arrive as plain
    strings. Both forms carry the same source text — normalize before comparing.
    """
    if isinstance(annotation, str):
        return annotation
    forward_arg = getattr(annotation, "__forward_arg__", None)
    return forward_arg if forward_arg is not None else str(annotation)


class TestP8BoundConstants:
    """D-06: the five bound constants are the single-source control surface."""

    def test_constants_import_with_documented_types_and_values(self):
        assert policies.MAX_SUPERVISOR_HOPS == 4
        assert isinstance(policies.MAX_SUPERVISOR_HOPS, int)

        assert policies.MAX_TOOL_CALLS == 4
        assert isinstance(policies.MAX_TOOL_CALLS, int)

        assert policies.WALL_CLOCK_S == 45.0
        assert isinstance(policies.WALL_CLOCK_S, float)

        assert policies.DEDUP_THRESHOLD == 0.95
        assert isinstance(policies.DEDUP_THRESHOLD, float)

        assert policies.CACHE_TTL_S == 21600
        assert isinstance(policies.CACHE_TTL_S, int)

    def test_int_constants_are_not_bool(self):
        # bool is an int subclass in Python; guard against a bool sneaking in.
        assert not isinstance(policies.MAX_SUPERVISOR_HOPS, bool)
        assert not isinstance(policies.MAX_TOOL_CALLS, bool)
        assert not isinstance(policies.CACHE_TTL_S, bool)


class TestSupervisorStateSuperset:
    """Pitfall #1: SupervisorState EXTENDS GraphState — it never forks it."""

    def test_annotations_are_graphstate_plus_the_supervisor_only_keys(self):
        assert set(SupervisorState.__annotations__) == (
            set(GraphState.__annotations__) | SUPERVISOR_ONLY_KEYS
        )

    def test_every_inherited_key_keeps_the_same_annotation(self):
        for key, ann in GraphState.__annotations__.items():
            assert key in SupervisorState.__annotations__, f"lost inherited key {key!r}"
            assert SupervisorState.__annotations__[key] == ann, (
                f"inherited key {key!r} was redefined "
                f"({ann!r} -> {SupervisorState.__annotations__[key]!r}) — "
                "Pitfall #1 state clobber"
            )

    def test_supervisor_only_keys_are_disjoint_from_graphstate(self):
        assert SUPERVISOR_ONLY_KEYS.isdisjoint(set(GraphState.__annotations__))
        for key in SUPERVISOR_ONLY_KEYS:
            assert key in SupervisorState.__annotations__

    def test_new_keys_have_expected_annotations(self):
        anns = SupervisorState.__annotations__
        assert _ann_str(anns["hops"]) == "int"
        assert _ann_str(anns["tool_calls"]) == "int"
        assert _ann_str(anns["tool_plan"]) == "list[str]"
        assert _ann_str(anns["tool_results"]) == "list[dict]"
        assert _ann_str(anns["started_at"]) == "float"
        assert _ann_str(anns["is_partial"]) == "bool"
        # 06.3-05 synthesize output channels.
        assert _ann_str(anns["fused_answer"]) == "FusedAnswer | None"
        assert _ann_str(anns["disclaimer"]) == "str"
