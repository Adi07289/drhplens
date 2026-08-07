"""
agent/tools/query_peers.py — the read-only peer-comparator tool node (D-01).

A deterministic `SupervisorState`-in / `SupervisorState`-out function in the shape
of `agent/nodes/retrieve.run`. It READS the committed peer record for the
single in-scope IPO (`data/peers/<drhp_id>.json`) via the existing
`pipelines.peers.load_peers` loader and returns the already-validated
`PeerRecord` as a provenance-tagged `tool_results` entry. It calls NO LLM and
burns NO quota — storage is the integration bus (D-01).

Security (T-6.3-PATH): `drhp_id` is gated through the catalogue allow-list
(`data.catalogue_loader.is_known_drhp_id`) BEFORE any `data/*` path is formed —
a non-allow-listed / traversal id is rejected (ValueError) before any read.
`load_peers` re-applies the same gate (defense in depth).

Honesty (P14): a MISSING record (FileNotFoundError) yields an honest
`abstain=True, record=None` — never a fabricated peer set.
"""
from __future__ import annotations

from agent.supervisor_state import SupervisorState
from data.catalogue_loader import is_known_drhp_id
from pipelines.peers import load_peers

TOOL_NAME = "query_peers"


def run(state: SupervisorState) -> SupervisorState:
    """Load the committed peer record for state["drhp_id"] (read-only, D-01).

    Appends one provenance-tagged entry to `tool_results`, pops itself from
    `tool_plan`, and increments `tool_calls` by exactly 1 — returning via the
    `{**state, ...}` overwrite convention every existing node uses.

    Raises:
        ValueError: if `drhp_id` is not in the catalogue allow-list — rejected
            BEFORE any `data/*` read (path-traversal mitigation, T-6.3-PATH).
    """
    drhp_id = state["drhp_id"]

    # Path-safety allow-list gate (T-6.3-PATH) runs FIRST — before any data/* path.
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to read peers for a "
            f"non-allow-listed id (catalogue allow-list, T-6.3-PATH)."
        )

    try:
        record = load_peers(drhp_id)
        result = {
            "tool": TOOL_NAME,
            "record": record.model_dump(),
            "provenance": f"data/peers/{drhp_id}.json",
            "abstain": False,
        }
    except FileNotFoundError:
        # Honest "no peer record" state — never a fabricated set (P14).
        result = {
            "tool": TOOL_NAME,
            "record": None,
            "provenance": None,
            "abstain": True,
        }

    plan = [t for t in state.get("tool_plan", []) if t != TOOL_NAME]
    return {
        **state,
        "tool_plan": plan,
        "tool_calls": state.get("tool_calls", 0) + 1,
        "tool_results": state.get("tool_results", []) + [result],
    }
