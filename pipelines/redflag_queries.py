"""
pipelines/redflag_queries.py — the 7 canned red-flag pre-compute queries.

Part of the Phase 3 red-flag contract (03-CONTEXT.md D3-01/D3-06, mirror of
pipelines/snapshot_queries.py). These strings are versioned like prompts: each
is run once per drhp_id through the EXISTING compiled agent (agent.graph.GRAPH)
— no new LLM path, no "red-flag mode" in the graph (reuse the grounded pipeline
so every field carries claim_id citations). Changing a query string changes
what gets cited into every committed red-flag JSON, so treat edits here as a
reviewable, deliberate change.

Keys are LOCKED to the 7 canonical red-flag fields in UI-SPEC R-1 fixed order,
and MUST stay in sync with agent.redflag_schema.REDFLAG_FIELD_KEYS (the
fields_keys_known validator rejects any drift):
  rpt_pct                -> Related-party transactions as a % of revenue
  ofs_vs_fresh           -> Offer-for-sale vs fresh-issue split
  promoter_pledge_pct    -> Promoter shareholding pledged, as a %
  customer_concentration -> Revenue concentration in top customers
  auditor_history        -> Auditor changes / qualifications / reservations
  debt_trajectory        -> Total borrowings trend over recent fiscals
  going_concern          -> Any going-concern / material-uncertainty statement
"""
from __future__ import annotations

REDFLAG_QUERIES: dict[str, str] = {
    "rpt_pct": (
        "What are the related-party transactions, and what do they amount to as "
        "a percentage of total revenue or income for the most recent fiscal years?"
    ),
    "ofs_vs_fresh": (
        "What is the split of the total issue between the fresh issue and the "
        "offer for sale — what portion of the proceeds goes to the company "
        "versus to selling shareholders?"
    ),
    "promoter_pledge_pct": (
        "Is any of the promoters' shareholding pledged or encumbered, and if so "
        "what percentage of the promoter holding is pledged?"
    ),
    "customer_concentration": (
        "What is the company's customer concentration — what share of revenue "
        "comes from the top customer or the top few customers, and is there a "
        "dependence on a small number of customers?"
    ),
    "auditor_history": (
        "What is the company's auditor history — have there been any changes of "
        "statutory auditors, and are there any qualifications, reservations, or "
        "adverse remarks in the auditors' reports?"
    ),
    "debt_trajectory": (
        "What is the trajectory of the company's total borrowings or debt over "
        "the last three to five fiscal years — is it rising or falling?"
    ),
    "going_concern": (
        "Do the auditors make any going-concern observation or note any material "
        "uncertainty about the company's ability to continue as a going concern?"
    ),
}
