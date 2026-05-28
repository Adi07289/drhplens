"""
Citation chip HTML renderer — UI-02, T-1-06 mitigation.

Contract per SKELETON §F:
- Emits <sup class="drhp-cite" data-claim-id="..."> chips
- XSS-escapes prose BEFORE chip interpolation (escape-then-interpolate)
- Deduplicates per D-03 (contiguous cluster → ONE chip at last position)
- Chip numbers reset per answer (D-01)
- Unknown placeholders fall through unchanged + log warning (PITFALL P5 debuggability)
- claim_id round-trips byte-for-byte from GroundedAnswer → data-claim-id (T-1-11)
"""
from __future__ import annotations

import html
import logging
import re

from agent.schemas import GroundedAnswer

logger = logging.getLogger(__name__)

# The canonical claim_id pattern per schemas.py
_PLACEHOLDER_RE = re.compile(r"\{\{(c_[a-z0-9]{6,16})\}\}")


def build_chip_html(claim_id: str, chip_n: int) -> str:
    """Build the HTML for a single citation chip.

    Pure function. HTML-escapes claim_id for defense-in-depth (T-1-06) even
    though the schema enforces ^c_[a-z0-9]{6,16}$ (no metacharacters possible).

    Returns the locked UI-SPEC HTML structure on one line:
      <sup class="drhp-cite" data-claim-id="..." tabindex="0" role="button"
           aria-describedby="cite-N-source" aria-label="citation N, opens source-text panel">[N]</sup>
    """
    esc_id = html.escape(claim_id, quote=True)
    return (
        f'<sup class="drhp-cite" data-claim-id="{esc_id}" tabindex="0" role="button" '
        f'aria-describedby="cite-{chip_n}-source" '
        f'aria-label="citation {chip_n}, opens source-text panel">[{chip_n}]</sup>'
    )


def render_answer_with_chips(answer: GroundedAnswer) -> tuple[str, dict[str, int]]:
    """Render answer prose with inline citation chips.

    Steps (T-1-06 escape-then-interpolate contract):
    1. Build valid_claim_ids set from answer.claims.
    2. Find all placeholder positions in the raw prose.
    3. HTML-escape the ENTIRE prose BEFORE chip substitution.
    4. Apply D-03 dedup: contiguous same-claim_id citations → ONE chip at last pos.
    5. Assign chip numbers in first-appearance order.
    6. Replace placeholders with chip HTML.

    Returns:
        (rendered_html, claim_id_to_chip_n)

    claim_id_to_chip_n maps each unique claim_id seen in the prose to its
    chip number (1-indexed, reset per answer per D-01).
    """
    valid_claim_ids = {c.claim_id for c in answer.claims}
    prose = answer.answer_prose

    # Step 2: find all placeholder positions in original prose
    matches = list(_PLACEHOLDER_RE.finditer(prose))

    # Track unknown placeholders for warning
    unknown_ids = {m.group(1) for m in matches if m.group(1) not in valid_claim_ids}
    for uid in unknown_ids:
        logger.warning(
            "Citation placeholder {{%s}} has no matching claim in GroundedAnswer — "
            "leaving unchanged (PITFALL P5: unsourced chip blocked)", uid
        )

    # Step 3: HTML-escape the prose BEFORE chip interpolation (T-1-06)
    # We must escape the prose text BUT preserve placeholder tokens so we can
    # replace them with chip HTML. Strategy: escape prose in segments between
    # placeholder positions, then reassemble.
    escaped_segments: list[str] = []
    prev_end = 0

    # Build list of (match, claim_id, is_valid) tuples
    match_info = [(m, m.group(1), m.group(1) in valid_claim_ids) for m in matches]

    # Determine which placeholder positions will receive chips (D-03 dedup)
    # D-03: contiguous cluster of same claim_id → keep only LAST occurrence
    # Two occurrences are "contiguous" if the text between them (stripped of
    # whitespace and sentence terminators) contains no other citation.
    def _is_contiguous_cluster(i: int) -> bool:
        """Return True if match i is the SAME claim_id as match i+1 and they
        are in a contiguous cluster (no other citation between them)."""
        if i + 1 >= len(match_info):
            return False
        cur_id = match_info[i][1]
        nxt_id = match_info[i + 1][1]
        if cur_id != nxt_id:
            return False
        # Text between current end and next start
        between = prose[match_info[i][0].end():match_info[i + 1][0].start()]
        between_stripped = between.strip(".!? \t\n\r")
        # Check that no other citation placeholder appears between them
        inner_matches = list(_PLACEHOLDER_RE.finditer(between))
        return len(inner_matches) == 0

    # Mark which matches are "suppressed" (all but last in each cluster)
    suppressed = set()
    for i in range(len(match_info)):
        if _is_contiguous_cluster(i):
            suppressed.add(i)

    # Step 5: assign chip numbers in first-appearance order
    claim_id_to_chip_n: dict[str, int] = {}
    next_chip_n = 1
    for i, (m, cid, is_valid) in enumerate(match_info):
        if not is_valid:
            continue
        if i in suppressed:
            continue
        if cid not in claim_id_to_chip_n:
            claim_id_to_chip_n[cid] = next_chip_n
            next_chip_n += 1

    # Step 3+6: build escaped output with chip substitutions
    result_parts: list[str] = []
    prev_end = 0
    for i, (m, cid, is_valid) in enumerate(match_info):
        # Escape prose text before this match
        prose_segment = prose[prev_end:m.start()]
        result_parts.append(html.escape(prose_segment, quote=False))

        if not is_valid:
            # Unknown placeholder: leave literal unchanged (no escaping of {{ }})
            result_parts.append(m.group(0))
        elif i in suppressed:
            # Deduped: remove placeholder, emit nothing
            pass
        else:
            # Emit chip
            chip_n = claim_id_to_chip_n[cid]
            result_parts.append(build_chip_html(cid, chip_n))

        prev_end = m.end()

    # Escape remaining prose after last match
    result_parts.append(html.escape(prose[prev_end:], quote=False))

    rendered_html = "".join(result_parts)
    return rendered_html, claim_id_to_chip_n
