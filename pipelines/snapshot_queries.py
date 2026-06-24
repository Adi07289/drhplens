"""
pipelines/snapshot_queries.py — the 6 canned snapshot pre-compute queries.

Part of the snapshot contract (02-RESEARCH.md §Pattern 3, D2-04, D2-05). These
strings are versioned like prompts: each is run once per drhp_id through the
EXISTING compiled agent (agent.graph.GRAPH) — no new LLM path, no "snapshot
mode" in the graph. Changing a query string changes what gets cited into every
committed snapshot JSON, so treat edits here as a reviewable, deliberate change.

Keys are locked to the 6 SNAP-02..07 field blocks (D2-05):
  metadata         -> SNAP-02 (price band, lot size, dates, issue size, fresh/OFS, BRLMs)
  business         -> SNAP-03 (plain-English business summary)
  financials       -> SNAP-04 (3-5yr revenue/profit/margins/debt/ROE/ROCE)
  risks            -> SNAP-05 (prioritized risk-factors summary)
  use_of_proceeds  -> SNAP-06 (use-of-proceeds breakdown; OFS-vs-fresh % foregrounded)
  promoter         -> SNAP-07 (promoter/management; pledging; prior matters)
"""
from __future__ import annotations

SNAPSHOT_QUERIES: dict[str, str] = {
    "metadata": (
        "What are the issue details: price band, lot size, issue dates, total "
        "issue size, the split between fresh issue and offer for sale, and the "
        "book running lead managers?"
    ),
    "business": (
        "Summarize the company's business model and what it does, in plain English."
    ),
    "financials": (
        "What are the restated revenue, profit/loss, EBITDA margin, total debt, "
        "ROE and ROCE for the last three to five fiscal years?"
    ),
    "risks": (
        "What are the most significant company-specific risk factors disclosed?"
    ),
    "use_of_proceeds": (
        "What are the objects of the issue — how will the fresh-issue proceeds "
        "be used, and what portion of the offer is an offer for sale versus "
        "fresh issue?"
    ),
    "promoter": (
        "Who are the promoters, what are their pre-issue and post-issue "
        "shareholdings, is any promoter shareholding pledged, and are there "
        "material prior legal or regulatory matters involving the promoters?"
    ),
}
