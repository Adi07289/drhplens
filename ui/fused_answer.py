"""ui/fused_answer.py — the fused multi-tool answer render surfaces (C1/C2/C3).

Render-only (P19, demo-safe): every function reads ONLY the cached ``FusedAnswer``
object handed to it — NO live LLM / Qdrant / agent call at render or on expand. The
render-only contract is pinned by the ``inspect.getsource`` + AST-import isolation test
in ``tests/unit/test_fused_answer_render.py`` (mirrors ``ui/eval_inline.py``).

The three surfaces (06.3-UI-SPEC, approved element-by-element 2026-08-05):

  C1 — one prose-first cited paragraph in a single ``<div class="drhp-fused">`` with an
       always-present mono provenance footer legend (``.drhp-fused-legend``) mapping
       every marker → its source. GMP appears ONLY as the caveated read-only gap (D-04),
       never colour-coded, never a model feature.

  C2 — per-number provenance markers, distinguishable AT A GLANCE (the honesty payoff):
       a DRHP-grounded ``Claim`` gets a NUMBERED superscript (``.drhp-prov--doc``) and
       reuses ``ui/expander.py``'s ``render_citation_expanders`` UNCHANGED (DRHP span +
       [open page]); a tool-derived ``ToolClaim`` gets a LETTERED superscript
       (``.drhp-prov--tool`` — ``ꜰ`` forecast / ``ᴾ`` peers / ``ᴳ`` GMP / ``ᴿ`` red-flags)
       expanding to a one-line source descriptor + surface link. A claim_id in the prose
       with no resolvable claim (dropped at cite-check, FM-3) renders NO marker.

  C3 — an honest-partial banner (``.drhp-partial`` — muted mono, DASHED NEUTRAL border,
       eyebrow ``INCOMPLETE ANSWER``) renders ABOVE the answer iff ``is_partial`` is True,
       naming what's missing. NEVER red/alarm — an incomplete answer is honest, not an
       error; it never accompanies a fabricated gap-fill (D-08).

Honesty invariant (non-negotiable): neutral mono, NO red/green/alarm colour anywhere;
accent is reserved for the marker hover/focus link affordance + the surface links. Every
untrusted scraped field (peer/GMP source, company names) is ``html.escape``d before it
reaches ``unsafe_allow_html`` markup (XSS T-6.3-XSS / T-1-06); inline markup only, no
script. All copy is imported from ``ui/copy.py`` (import-time scrubber covers it).
"""
from __future__ import annotations

import html
import re

import streamlit as st

from agent.schemas import Claim, FusedAnswer, GroundedAnswer, ToolClaim
from ui import copy as _copy
from ui.expander import SEBI_PROSPECTUS_URL, render_citation_expanders

# The canonical claim_id placeholder pattern (matches ui/chip.py; schemas.py §Claim).
_PLACEHOLDER_RE = re.compile(r"\{\{(c_[a-z0-9]{6,16})\}\}")

# Lettered tool markers (UI-SPEC C2) — distinct from the numbered DRHP markers so
# doc-grounded vs data-grounded is legible at a glance. GMP folds into query_forecast
# (D-04) but carries its OWN marker so a GMP figure is never mistaken for a model band.
_MARKER_FORECAST = "ꜰ"   # ꜰ
_MARKER_PEERS = "ᴾ"      # ᴾ
_MARKER_GMP = "ᴳ"        # ᴳ
_MARKER_REDFLAGS = "ᴿ"  # ᴿ

# In-page fragment anchors on the co-located snapshot page (D2-08). Same-page, so
# never a dead link; worst case a no-scroll. The renderer keeps these as code
# constants (URLs, not copy) — only the link TEXT is centralized in ui/copy.py.
_LINK_FORECAST = "#forecast"
_LINK_PEERS = "#peers"
_LINK_SNAPSHOT = "#snapshot"

# The unaddressed sentinel the synthesize node writes on a budget-trip (mirrors
# ``agent.nodes.synthesize._UNADDRESSED_BUDGET``) — kept as a literal so this
# render-only module imports NO agent code.
_BUDGET_TRIP_SENTINEL = "ran out of steps"


# ---------------------------------------------------------------------------
# C2 — marker classification + HTML
# ---------------------------------------------------------------------------


def _tool_marker(claim: ToolClaim) -> str:
    """Return the lettered marker glyph for a ToolClaim (GMP detected via its
    ``source_record_id`` field-path, which resolves against the display-only
    ``gmp_gap`` block — D-04). Falls back to the GMP glyph only if the source_tool
    is somehow unknown (defensive; classify already clamps the tool set)."""
    _prov, _sep, field_path = (claim.source_record_id or "").partition("#")
    if field_path.startswith("gmp_gap") or field_path.startswith("gmp"):
        return _MARKER_GMP
    return {
        "query_forecast": _MARKER_FORECAST,
        "query_peers": _MARKER_PEERS,
        "query_redflags": _MARKER_REDFLAGS,
    }.get(claim.source_tool, _MARKER_GMP)


def _doc_marker_html(claim_id: str, chip_n: int) -> str:
    """A NUMBERED DRHP superscript marker (keyboard-focusable, accent on hover/focus)."""
    esc_id = html.escape(claim_id, quote=True)
    return (
        f'<sup class="drhp-prov drhp-prov--doc" data-claim-id="{esc_id}" '
        f'tabindex="0" role="button" '
        f'aria-label="DRHP citation {chip_n}, opens source text">{chip_n}</sup>'
    )


def _tool_marker_html(claim_id: str, marker: str, aria: str) -> str:
    """A LETTERED tool superscript marker (keyboard-focusable, accent on hover/focus)."""
    esc_id = html.escape(claim_id, quote=True)
    return (
        f'<sup class="drhp-prov drhp-prov--tool" data-claim-id="{esc_id}" '
        f'tabindex="0" role="button" '
        f'aria-label="{html.escape(aria, quote=True)} source, opens descriptor">'
        f'{html.escape(marker)}</sup>'
    )


# ---------------------------------------------------------------------------
# C1 — fused prose (escape-then-interpolate, mirrors ui/chip.py)
# ---------------------------------------------------------------------------


def render_fused_prose(fused: FusedAnswer) -> tuple[str, dict[str, int]]:
    """Render the fused answer prose into ONE ``<div class="drhp-fused">`` with inline
    provenance markers (C1/C2). Returns ``(html, doc_marker_map)`` where
    ``doc_marker_map`` maps each DRHP ``Claim`` id → its 1-indexed chip number (in
    first-appearance order) for the reused citation expander + the footer legend.

    Escape-then-interpolate (T-1-06): the prose is HTML-escaped in the segments
    BETWEEN markers, then each ``{{claim_id}}`` is replaced by its marker HTML. A
    marker whose claim was DROPPED (not present in ``fused.claims`` — FM-3) renders
    NOTHING (never a broken/raw citation)."""
    claims_by_id: dict[str, Claim | ToolClaim] = {c.claim_id: c for c in fused.claims}
    prose = fused.answer_prose or ""

    doc_marker_map: dict[str, int] = {}
    next_n = 1
    parts: list[str] = []
    prev_end = 0

    for m in _PLACEHOLDER_RE.finditer(prose):
        cid = m.group(1)
        parts.append(html.escape(prose[prev_end:m.start()], quote=False))
        prev_end = m.end()

        claim = claims_by_id.get(cid)
        if claim is None:
            # Dropped/unresolved at cite-check (FM-3) — render no marker at all.
            continue
        if isinstance(claim, ToolClaim):
            marker = _tool_marker(claim)
            parts.append(_tool_marker_html(cid, marker, claim.source_tool))
        else:  # DRHP-grounded Claim → numbered marker
            if cid not in doc_marker_map:
                doc_marker_map[cid] = next_n
                next_n += 1
            parts.append(_doc_marker_html(cid, doc_marker_map[cid]))

    parts.append(html.escape(prose[prev_end:], quote=False))
    body = "".join(parts)
    return f'<div class="drhp-fused">{body}</div>', doc_marker_map


# ---------------------------------------------------------------------------
# C1 — provenance footer legend (always present when the answer carries markers)
# ---------------------------------------------------------------------------


def _tool_legend_segment(marker: str) -> str:
    """The legend text for a lettered tool marker (from ui/copy.py)."""
    return {
        _MARKER_FORECAST: _copy.FUSED_LEGEND_FORECAST,
        _MARKER_PEERS: _copy.FUSED_LEGEND_PEERS,
        _MARKER_GMP: _copy.FUSED_LEGEND_GMP,
        _MARKER_REDFLAGS: _copy.FUSED_LEGEND_REDFLAGS,
    }.get(marker, _copy.FUSED_LEGEND_GMP)


def build_provenance_legend(fused: FusedAnswer, doc_marker_map: dict[str, int]) -> str:
    """Build the always-present mono footer legend mapping markers → sources (C1).

    Numbered DRHP entries (in chip order) first, then each DISTINCT lettered tool
    marker (in first-appearance order). Returns ``""`` when the answer carries no
    markers (a claim-less honest partial has nothing to map — no empty legend line)."""
    claims_by_id: dict[str, Claim | ToolClaim] = {c.claim_id: c for c in fused.claims}
    segments: list[str] = []

    for cid, chip_n in sorted(doc_marker_map.items(), key=lambda kv: kv[1]):
        claim = claims_by_id.get(cid)
        page = getattr(claim, "drhp_page", None)
        drhp = _copy.FUSED_LEGEND_DRHP_TEMPLATE.format(page=html.escape(str(page)))
        segments.append(
            f'<span class="drhp-fused-legend-item">{chip_n} {drhp}</span>'
        )

    seen: set[str] = set()
    for claim in fused.claims:
        if not isinstance(claim, ToolClaim):
            continue
        marker = _tool_marker(claim)
        if marker in seen:
            continue
        seen.add(marker)
        segments.append(
            f'<span class="drhp-fused-legend-item">'
            f'{html.escape(marker)} {html.escape(_tool_legend_segment(marker))}</span>'
        )

    if not segments:
        return ""
    return f'<div class="drhp-fused-legend">{"".join(segments)}</div>'


# ---------------------------------------------------------------------------
# C2 — expander descriptors (DRHP Claim reuses the existing citation expander;
#      ToolClaim gets a sibling one-line source descriptor)
# ---------------------------------------------------------------------------


def build_drhp_expanders(fused: FusedAnswer, doc_marker_map: dict[str, int]) -> list[dict]:
    """DRHP ``Claim`` expander descriptors — REUSES ``render_citation_expanders``
    UNCHANGED (UI-SPEC C2: do NOT rebuild). Wraps the Claim-only subset of the union
    in a ``GroundedAnswer`` so the existing expander resolves them exactly as the
    Phase-1 chat path does (DRHP span + [open page])."""
    doc_claims = [c for c in fused.claims if isinstance(c, Claim)]
    if not doc_claims:
        return []
    # answer_prose is not consumed by the expander (it iterates claims + the map);
    # a Claim-only GroundedAnswer keeps the reuse byte-identical to the chat path.
    ga = GroundedAnswer(answer_prose=fused.answer_prose, claims=doc_claims)
    return render_citation_expanders(ga, doc_marker_map)


def _tool_descriptor_copy(marker: str) -> tuple[str, str, str, str]:
    """Return ``(label, body, link_text, link_url)`` for a lettered tool marker.
    GMP's body is the mandatory D-04 caveat; the forecast body labels it the
    honest GMP-free calibrated model (no overclaim)."""
    if marker == _MARKER_PEERS:
        return (
            _copy.FUSED_EXPANDED_PEERS_LABEL,
            _copy.FUSED_EXPANDED_PEERS_BODY,
            _copy.FUSED_EXPANDED_PEERS_LINK,
            _LINK_PEERS,
        )
    if marker == _MARKER_GMP:
        return (
            _copy.FUSED_EXPANDED_GMP_LABEL,
            _copy.FUSED_GMP_CHAT_CAVEAT,  # D-04 mandatory caveat
            _copy.FUSED_EXPANDED_GMP_LINK,
            _LINK_FORECAST,
        )
    if marker == _MARKER_REDFLAGS:
        return (
            _copy.FUSED_EXPANDED_REDFLAGS_LABEL,
            _copy.FUSED_EXPANDED_REDFLAGS_BODY,
            _copy.FUSED_EXPANDED_REDFLAGS_LINK,
            _LINK_SNAPSHOT,
        )
    return (
        _copy.FUSED_EXPANDED_FORECAST_LABEL,
        _copy.FUSED_EXPANDED_FORECAST_BODY,
        _copy.FUSED_EXPANDED_FORECAST_LINK,
        _LINK_FORECAST,
    )


def build_tool_source_descriptors(fused: FusedAnswer) -> list[dict]:
    """One expander descriptor per ToolClaim (the sibling path to the DRHP expander).

    Reads ONLY the cached ToolClaim object — no live call, no file re-read (P19). Every
    untrusted field is HTML-escaped (T-6.3-XSS). One descriptor per unique claim_id."""
    seen: set[str] = set()
    results: list[dict] = []
    for claim in fused.claims:
        if not isinstance(claim, ToolClaim):
            continue
        if claim.claim_id in seen:
            continue
        seen.add(claim.claim_id)
        marker = _tool_marker(claim)
        label, body, link_text, link_url = _tool_descriptor_copy(marker)
        results.append({
            "claim_id": claim.claim_id,
            "marker": marker,
            "label": html.escape(label),
            "body": html.escape(body),
            "value": html.escape(str(claim.value)),
            "source_record_id": html.escape(claim.source_record_id or ""),
            "link_text": html.escape(link_text),
            "link_url": link_url,  # internal same-page fragment — safe (code constant)
        })
    return results


# ---------------------------------------------------------------------------
# C3 — honest-partial banner (muted mono, dashed neutral — NEVER red/alarm)
# ---------------------------------------------------------------------------


def _is_budget_trip(unaddressed: list[str]) -> bool:
    """The partial was a hard budget-trip (vs a single-tool abstain/error)."""
    return any(_BUDGET_TRIP_SENTINEL in (u or "") for u in (unaddressed or []))


def render_partial_banner(fused: FusedAnswer) -> str | None:
    """Return the C3 honest-partial banner HTML iff ``is_partial`` is True, else None.

    Two copy variants (UI-SPEC): a budget-trip (generic "stopped early") and a
    source-specific tool-abstain ("no forecast band … answering from the DRHP + peers
    only"). Muted mono, dashed NEUTRAL border, eyebrow ``INCOMPLETE ANSWER`` — never
    red/alarm; it names the gap, never fabricates a fill (D-08)."""
    if not getattr(fused, "is_partial", False):
        return None
    body = (
        _copy.FUSED_PARTIAL_BUDGET_BODY
        if _is_budget_trip(getattr(fused, "unaddressed", []) or [])
        else _copy.FUSED_PARTIAL_TOOL_ABSTAIN_BODY
    )
    # quote=False: this is element text, not an attribute — keep apostrophes literal.
    return (
        '<div class="drhp-partial" role="status" aria-live="polite">'
        f'<span class="drhp-partial-eyebrow">'
        f'{html.escape(_copy.FUSED_PARTIAL_EYEBROW, quote=False)}</span>'
        f'<span class="drhp-partial-body">{html.escape(body, quote=False)}</span>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Streamlit consumer (render-only; the pure builders above are the tested seam)
# ---------------------------------------------------------------------------


def render_fused_answer(fused: FusedAnswer, *, key: str = "") -> None:
    """Render the full fused answer surface: C3 banner (if partial) ABOVE, then the
    C1 prose + always-present provenance legend, then the C2 expanders (DRHP Claims
    via the reused citation expander, ToolClaims via the sibling descriptor path).

    Render-only: consumes ONLY the cached ``FusedAnswer`` — no live call on render or
    on expand (P19; mirrors the methodology-pane no-client rule)."""
    banner = render_partial_banner(fused)
    if banner is not None:
        st.markdown(banner, unsafe_allow_html=True)

    prose_html, doc_marker_map = render_fused_prose(fused)
    st.markdown(prose_html, unsafe_allow_html=True)

    legend = build_provenance_legend(fused, doc_marker_map)
    if legend:
        st.markdown(legend, unsafe_allow_html=True)

    # C2 — DRHP Claim expanders (existing citation expander, unchanged).
    for exp in build_drhp_expanders(fused, doc_marker_map):
        with st.expander(exp["label"], expanded=False):
            st.markdown(
                f'<div class="drhp-snippet">{exp["snippet"]}</div>',
                unsafe_allow_html=True,
            )
            page = exp["page_start"]
            st.markdown(
                f'[{_copy.FUSED_OPEN_PAGE_TEMPLATE.format(page=page)}]'
                f'({SEBI_PROSPECTUS_URL}#page={page})'
            )
            st.markdown(
                f'<div class="drhp-snippet-metadata">{exp["metadata_footer"]}</div>',
                unsafe_allow_html=True,
            )

    # C2 — ToolClaim expanders (sibling one-line source descriptor + surface link).
    for desc in build_tool_source_descriptors(fused):
        with st.expander(f'{desc["marker"]} {desc["label"]}', expanded=False):
            st.markdown(
                f'<div class="drhp-prov-src">{desc["body"]}</div>',
                unsafe_allow_html=True,
            )
            if desc["link_url"]:
                st.markdown(f'[{desc["link_text"]} →]({desc["link_url"]})')
