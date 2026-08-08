"""
agent/supervisor.py — the bounded multi-tool supervisor (D-02/D-05/D-06/D-08).

The centerpiece of Phase 6.3: a hand-rolled bounded supervisor that WRAPS the
existing 10-node DRHP-RAG graph UNCHANGED as a sub-agent (D-02), wires the single
bounded ``classify`` hop + the read-only tool nodes + the terminal ``synthesize``
node, and routes them with a DETERMINISTIC counter-bounded ``route`` — the real P8
guard (D-06). It mirrors ``agent/graph.py``'s four load-bearing patterns:

  1. Counter-bounded conditional-edge router (a generalization of ``_route_scrub``):
     ``route`` halts to ``synthesize`` on hop / tool-call / wall-clock budget BEFORE
     any framework limit — zero free LangGraph cycles (D-06).
  2. ``build_supervisor(checkpointer=None)`` + ``StateGraph`` assembly (the existing
     ``build_graph`` shape). The existing compiled graph is embedded AS a node via a
     thin wrapper — the subgraph topology + its 10 nodes stay byte-for-byte unchanged
     (D-02); ``build_graph(checkpointer=None)`` so the PARENT owns persistence
     (AI-SPEC Pitfall #2).
  3. Module-level compiled singleton ``SUPERVISOR = build_supervisor(MemorySaver())``
     — RESEARCH caveat (a): use ``MemorySaver``, NOT a disk-backed checkpointer; a
     fresh ``thread_id`` per run makes durability moot and the ``/tmp`` ephemerality
     gotcha irrelevant. The cross-run "TTL that spans runs" is the SEPARATE
     semantic-cache module's job, not the checkpointer's.
  4. ``invoke_supervisor`` — the entry point mirroring ``invoke_with_tracing``'s
     fresh-``thread_id`` + Langfuse-trace contract, with ONE deliberate delta: a
     ``GraphRecursionError`` (the ``recursion_limit`` crash backstop, caveat d) is
     CAUGHT and converted to an honest labelled partial (D-08) — NEVER re-raised as a
     crash to the user (unlike ``invoke_with_tracing``).

The P8 bound is the explicit ``hops`` / ``tool_calls`` / wall-clock counter in
``route`` — NOT ``recursion_limit`` (caveat d). ``recursion_limit`` is set low (~50)
purely as a last-resort crash backstop.
"""
from __future__ import annotations

import time
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

from app.observability.trace_enrichment import (
    count_tool_calls,
    emit_enriched_trace,
    flush,
)

from agent.graph import build_graph
from agent.nodes import classify, synthesize
from agent.policies import (
    MAX_SUPERVISOR_HOPS,
    MAX_TOOL_CALLS,
    WALL_CLOCK_S,
)
from agent.schemas import FusedAnswer, RefusalResponse
from agent.state import GraphState
from agent.supervisor_state import SupervisorState
from agent.tools import query_forecast, query_peers, query_redflags

# The GraphState channels the embedded subgraph recognizes — used to hand the
# subgraph ONLY its own keys (the supervisor-only keys are re-merged after).
_GRAPHSTATE_KEYS: frozenset[str] = frozenset(GraphState.__annotations__)

# The embedded DRHP-RAG sub-agent (D-02): the existing 10-node compiled graph,
# UNCHANGED. checkpointer=None so the parent SUPERVISOR owns persistence (Pitfall #2).
DRHP_RAG_SUBGRAPH = build_graph(checkpointer=None)


# ---------------------------------------------------------------------------
# The embedded DRHP-RAG node — a thin wrapper around the UNCHANGED subgraph.
#
# The compiled subgraph reads/writes GraphState only; it cannot pop itself from
# ``tool_plan`` or increment ``tool_calls`` (those are supervisor-only keys). The
# wrapper invokes the subgraph unchanged, then applies the tool-node bookkeeping the
# router relies on (pop-self + ``+1 tool_calls``) — the same contract the read-only
# tool nodes honour. An infra failure inside the subgraph (e.g. Qdrant unreachable)
# degrades to the existing ``infrastructure_error`` refusal (Rule 2 robustness),
# never a crash to the caller.
# ---------------------------------------------------------------------------


def _drhp_rag_node(state: SupervisorState) -> SupervisorState:
    """Run the embedded DRHP-RAG subgraph, then apply supervisor bookkeeping."""
    sub_input = {k: state[k] for k in _GRAPHSTATE_KEYS if k in state}
    try:
        sub_out = DRHP_RAG_SUBGRAPH.invoke(sub_input)
    except Exception:  # noqa: BLE001 — never crash the supervisor on subgraph infra failure
        sub_out = {
            "refusal": RefusalResponse(
                reason="infrastructure_error",
                explanation=(
                    "The DRHP reading step is temporarily unavailable. This is a "
                    "free-tier infrastructure hiccup, not a problem with your question."
                ),
                reformulation_suggestions=[],
            ),
            "grounded_answer": None,
            "all_claims_grounded": False,
        }

    plan = [t for t in state.get("tool_plan", []) if t != "drhp_rag"]
    return {
        **state,
        **sub_out,  # subgraph outputs (grounded_answer / refusal / all_claims_grounded / …)
        "tool_plan": plan,
        "tool_calls": state.get("tool_calls", 0) + 1,
    }


# ---------------------------------------------------------------------------
# The deterministic bounded router — the real P8 guard (D-06).
# ---------------------------------------------------------------------------


def route(state: SupervisorState) -> str:
    """Deterministic budget guardrail (D-06): the counter trips BEFORE any framework
    limit. Over budget (hops / tool-calls / wall-clock) OR an empty plan ⇒ halt to
    ``synthesize`` (which honest-partials an unfinished plan, D-08); otherwise
    dispatch the next pending tool. ``MAX_SUPERVISOR_HOPS`` / ``MAX_TOOL_CALLS`` are
    read as MODULE globals so the stress suite can monkeypatch them here."""
    over_budget = (
        state.get("hops", 0) > MAX_SUPERVISOR_HOPS
        or state.get("tool_calls", 0) >= MAX_TOOL_CALLS
        or (time.monotonic() - state.get("started_at", time.monotonic())) > WALL_CLOCK_S
    )
    if over_budget or not state.get("tool_plan"):
        return "synthesize"
    return state["tool_plan"][0]


# Every value ``route`` can return maps to a node. The tool names are already
# clamped to this allow-list by ``classify`` (D-05), so no unknown key can escape.
_ROUTE_MAP: dict[str, str] = {
    "drhp_rag": "drhp_rag",
    "query_peers": "query_peers",
    "query_forecast": "query_forecast",
    "query_redflags": "query_redflags",
    "synthesize": "synthesize",
}

_TOOL_NODES: tuple[str, ...] = (
    "drhp_rag",
    "query_peers",
    "query_forecast",
    "query_redflags",
)


# ---------------------------------------------------------------------------
# Graph builder — mirrors agent/graph.build_graph shape (do NOT fork it).
# ---------------------------------------------------------------------------


def build_supervisor(checkpointer=None):
    """Build + compile the bounded supervisor ``StateGraph(SupervisorState)``.

    START → classify → route → {tool nodes … re-enter route} → synthesize → END.
    Each tool node (including the embedded ``drhp_rag`` wrapper) pops itself from
    ``tool_plan`` + increments ``tool_calls``, then re-enters the counter-bounded
    router — a conditional edge, NOT a free LangGraph cycle (the ``_route_scrub``
    pattern generalized, D-06).

    Args:
        checkpointer: Optional LangGraph checkpointer. ``MemorySaver`` for the app +
            tests (caveat a); ``None`` compiles without checkpointing (unit tests).
    """
    g = StateGraph(SupervisorState)

    g.add_node("classify", classify.run)
    g.add_node("drhp_rag", _drhp_rag_node)  # the UNCHANGED subgraph, wrapped (D-02)
    g.add_node("query_peers", query_peers.run)
    g.add_node("query_forecast", query_forecast.run)
    g.add_node("query_redflags", query_redflags.run)
    g.add_node("synthesize", synthesize.run)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route, _ROUTE_MAP)
    # Each tool re-enters the bounded router (counter-bounded, zero free cycles).
    for tool in _TOOL_NODES:
        g.add_conditional_edges(tool, route, _ROUTE_MAP)
    g.add_edge("synthesize", END)

    return g.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level compiled singleton (parity with agent/graph.GRAPH).
# ---------------------------------------------------------------------------

SUPERVISOR = build_supervisor(MemorySaver())
"""The compiled bounded supervisor singleton. Uses ``MemorySaver`` (caveat a — not a
disk-backed checkpointer); a fresh ``thread_id`` per invoke isolates runs, so
durability is moot and the HF ``/tmp`` ephemerality gotcha does not apply. Used by
``invoke_supervisor`` and the Wave-4 Streamlit chat surface."""


# ---------------------------------------------------------------------------
# Honest-partial builder (D-08) — the crash-safe degradation.
# ---------------------------------------------------------------------------


def _honest_partial(state: dict, reason: str) -> dict:
    """Return an honest labelled partial (D-08) — never a crash, never a fabrication.

    Used when the ``recursion_limit`` crash backstop fires (``GraphRecursionError``,
    caveat d) before ``synthesize`` could run. Surfaces whatever grounded content
    already exists; otherwise a content-free honest partial explicitly labelled
    incomplete. Mirrors the ``synthesize`` honest-partial shape."""
    partial = FusedAnswer(
        answer_prose=synthesize.HONEST_PARTIAL_PROSE,
        claims=[],
        is_partial=True,
        unaddressed=[f"{synthesize._UNADDRESSED_BUDGET} ({reason})"],
    )
    return {
        **state,
        "fused_answer": partial,
        "refusal": None,
        "is_partial": True,
        "disclaimer": synthesize._disclaimer(),
    }


# ---------------------------------------------------------------------------
# Entry point — mirrors invoke_with_tracing, but crash-degrades (never re-raises).
# ---------------------------------------------------------------------------


def invoke_supervisor(question: str, drhp_id: str) -> dict:
    """Run the bounded supervisor end-to-end and return the final validated state.

    Mints a FRESH ``thread_id`` per run (mandatory once a checkpointer is attached —
    the note in ``invoke_with_tracing`` records this silently zeroed an eval once) and
    sets ``recursion_limit=50`` as a pure crash BACKSTOP (caveat d — NOT the P8 bound;
    the ``route`` counter is the real bound). Initializes the SupervisorState counters
    (``hops=0``, ``tool_calls=0``, ``tool_plan=[]``, ``tool_results=[]``,
    ``started_at=time.monotonic()``, ``is_partial=False``, ``regenerate_attempts=0``).

    A ``GraphRecursionError`` is caught and converted to an honest labelled partial
    (D-08) — the supervisor NEVER surfaces a crash to the user (the one deliberate
    delta from ``invoke_with_tracing``, which re-raises). Emits an enriched Langfuse
    trace + ``flush()`` exactly as ``agent/graph.py`` does (a no-op when Langfuse is
    disabled, so offline/CI behaviour is byte-identical to a bare invoke).
    """
    config: dict = {
        "configurable": {"thread_id": f"run-{uuid.uuid4()}"},
        "recursion_limit": 50,  # crash backstop only (caveat d) — NOT the P8 bound
    }
    init: dict = {
        # GraphState channels (subgraph contract) — safe defaults.
        "question": question,
        "drhp_id": drhp_id,
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": False,
        "gate1_max_score": 0.0,
        "sub_questions": [question],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
        # SupervisorState-only channels (the P8 loop guard).
        "hops": 0,
        "tool_calls": 0,
        "tool_plan": [],
        "tool_results": [],
        "started_at": time.monotonic(),
        "is_partial": False,
    }

    start = time.perf_counter()
    try:
        final_state = SUPERVISOR.invoke(init, config=config)
    except GraphRecursionError:
        # The recursion_limit crash backstop fired — degrade to an honest partial
        # (D-08), never a crash to the user. Still emit a crash-classified trace.
        latency_ms = (time.perf_counter() - start) * 1000.0
        final_state = _honest_partial(init, reason="budget_trip")
        emit_enriched_trace(
            question, final_state, latency_ms, tool_calls=0, cost_usd=0.0, crashed=True
        )
        flush()
        return final_state

    latency_ms = (time.perf_counter() - start) * 1000.0
    emit_enriched_trace(
        question,
        final_state,
        latency_ms,
        tool_calls=count_tool_calls(final_state),
        cost_usd=0.0,
    )
    flush()
    return final_state
