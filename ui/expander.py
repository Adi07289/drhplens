"""
Citation source-snippet inline expander wrapper.

Returns structured expander descriptors — one per unique claim_id in the answer.
The Streamlit consumer (app.py) iterates and emits one st.expander per dict.

SEBI canonical Swiggy prospectus URL (Phase 1 single-source):
"""
from __future__ import annotations

import html as _html

from agent.schemas import GroundedAnswer

# Canonical Phase 1 Swiggy prospectus URL (per 01-01-PLAN.md Task 2)
SEBI_PROSPECTUS_URL = (
    "https://www.sebi.gov.in/filings/public-issues/nov-2024/"
    "swiggy-limited-prospectus_88320.html"
)


def render_citation_expanders(
    answer: GroundedAnswer,
    claim_id_to_chip_n: dict[str, int],
) -> list[dict]:
    """Return one expander descriptor per unique claim_id in answer.claims.

    Ordered by chip_n ascending. One expander per deduped chip (Phase 1: first
    source per claim; Phase 3 METHOD-01 may surface all sources).

    Every string field is HTML-escaped (T-1-06 — DRHP snippet text may contain
    HTML-meaningful characters like < or &).

    Returns list of dicts shaped:
        {
          "chip_n": int,
          "claim_id": str,
          "label": str,         # "[N] DRHP page P · Section"
          "snippet": str,       # HTML-escaped verbatim DRHP source text
          "source_url": str,    # SEBI URL + #page=N anchor
          "page_start": int,
          "section": str,
          "metadata_footer": str,
        }
    """
    seen_claim_ids: set[str] = set()
    results: list[dict] = []

    for claim in answer.claims:
        cid = claim.claim_id
        if cid in seen_claim_ids:
            continue
        seen_claim_ids.add(cid)

        # Only include claims that were assigned a chip number
        if cid not in claim_id_to_chip_n:
            continue

        chip_n = claim_id_to_chip_n[cid]
        source = claim.sources[0]  # Phase 1: first source only

        page_start = source.page_start
        section = source.section

        # Snippet: prefer verbatim_span from source, fall back to claim's verbatim_span
        snippet_raw = source.verbatim_span or claim.verbatim_span or ""

        label = f"[{chip_n}] DRHP page {page_start} · {section}"
        source_url = f"{SEBI_PROSPECTUS_URL}#page={page_start}"
        metadata_footer = (
            f"claim_id: {cid} · DRHP page {page_start} · section \"{section}\""
        )

        results.append({
            "chip_n": chip_n,
            "claim_id": cid,
            "label": _html.escape(label),
            "snippet": _html.escape(snippet_raw),
            "source_url": source_url,  # URL is safe (constructed from constants + int)
            "page_start": page_start,
            "section": _html.escape(section),
            "metadata_footer": _html.escape(metadata_footer),
        })

    # Sort by chip_n ascending
    results.sort(key=lambda d: d["chip_n"])
    return results
