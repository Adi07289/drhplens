"""
pipelines/peer_queries.py — the canned DRHP peer-SET pre-compute query (PEER-01).

Part of the Phase 4 peer-comparator contract (04-CONTEXT.md D4-04, mirror of
pipelines/redflag_queries.py / snapshot_queries.py). This string is versioned
like a prompt: it is run once per drhp_id through the EXISTING compiled agent
(agent.graph.GRAPH) — no new LLM path, no "peer mode" in the graph (reuse the
grounded pipeline so the peer SET carries claim_id citations and its DRHP page).
Changing this query changes what gets cited into every committed peer JSON, so
treat edits here as a reviewable, deliberate change.

The peer MULTIPLES (P/E, P/B, EV/EBITDA, ROE) are NOT extracted from the DRHP —
they are fetched per-cell from the source-priority ladder in
pipelines/peer_sources.py at precompute time (PEER-02, D4-05).
"""
from __future__ import annotations

PEER_SET_QUERY: str = (
    "In the 'Basis for Issue Price' or 'Comparison with Listed Industry Peers' "
    "section, which listed companies does the company name as its peers, and on "
    "what DRHP page? List each peer company name exactly as disclosed."
)
