"""
agent/tools/query_redflags.py — the read-only red-flag / financials tool node (D-01).

A deterministic `SupervisorState`-in / `SupervisorState`-out function in the shape
of `agent/nodes/retrieve.run`. It READS the committed red-flag record for the
single in-scope IPO (`data/redflag/<drhp_id>.json`) via the existing
`pipelines.redflag.load_redflag` loader and returns the already-validated
`RedFlagRecord` as a provenance-tagged `tool_results` entry. It calls NO LLM and
burns NO quota — storage is the integration bus (D-01).

Security (T-6.3-PATH): `drhp_id` is gated through the catalogue allow-list
(`data.catalogue_loader.is_known_drhp_id`) BEFORE any `data/*` path is formed —
a non-allow-listed / traversal id is rejected (ValueError) before any read.
`load_redflag` re-applies the same gate (defense in depth).

Honesty (P14): a MISSING record (FileNotFoundError) yields an honest
`abstain=True, record=None` — never a fabricated red-flag table.
"""
from __future__ import annotations

from agent.supervisor_state import SupervisorState
from data.catalogue_loader import is_known_drhp_id
from pipelines.redflag import load_redflag

TOOL_NAME = "query_redflags"


def run(state: SupervisorState) -> SupervisorState:
    """Load the committed red-flag record for state["drhp_id"] (read-only, D-01).

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
            f"Unknown drhp_id={drhp_id!r}; refusing to read red-flags for a "
            f"non-allow-listed id (catalogue allow-list, T-6.3-PATH)."
        )

    try:
        record = load_redflag(drhp_id)
        result = {
            "tool": TOOL_NAME,
            "record": record.model_dump(),
            "provenance": f"data/redflag/{drhp_id}.json",
            "abstain": False,
        }
    except FileNotFoundError:
        # Honest "no red-flag record" state — never a fabricated table (P14).
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
