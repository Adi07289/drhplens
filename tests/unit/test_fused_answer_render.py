"""Unit tests — the fused multi-tool answer render surfaces (C1/C2/C3, 06.3-08).

Pins the render-only honesty contract on ``ui.fused_answer`` (mirrors the
``ui/eval_inline.py`` posture):

  (a) read-only isolation — the module imports NO live-call client (no LLM / Qdrant /
      agent-graph / supervisor); expansion reads the cached ``FusedAnswer`` object only
      (P19) — AST import-allowlist + inspect.getsource forbidden-token scan;
  (b) C2 markers — a DRHP ``Claim`` renders a NUMBERED marker, a tool ``ToolClaim``
      renders a LETTERED marker (ꜰ/ᴾ/ᴳ/ᴿ), distinguishable at a glance;
  (c) FM-3 — a dropped/unresolved ToolClaim (claim absent from ``claims``) renders NO
      marker (never a broken citation);
  (d) C1 — the always-present mono provenance legend maps every marker → its source;
  (e) C3 — the ``.drhp-partial`` banner shows iff ``is_partial=True`` (muted, dashed,
      never red/alarm); two copy variants (tool-abstain vs budget-trip);
  (f) D-04 — a GMP figure carries the ᴳ marker + the mandatory display-only caveat;
  (g) no verdict colour — the appended ``.drhp-fused*/.drhp-prov*/.drhp-partial*`` CSS
      block uses NO red/green/destructive token (grep the shipped stylesheet).

Task 2 (below the divider) pins the chat routing through the multi-tool supervisor.
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import ui.fused_answer as fused_answer
from agent.schemas import Claim, FusedAnswer, RetrievedChunkRef, ToolClaim
from ui.copy import (
    FUSED_GMP_CHAT_CAVEAT,
    FUSED_PARTIAL_BUDGET_BODY,
    FUSED_PARTIAL_EYEBROW,
    FUSED_PARTIAL_TOOL_ABSTAIN_BODY,
)
from ui.fused_answer import (
    build_provenance_legend,
    build_tool_source_descriptors,
    render_fused_answer,
    render_fused_prose,
    render_partial_banner,
)

_DRHP_ID = "swiggy_2024_11"
_CSS_PATH = Path(__file__).resolve().parents[2] / "app" / "static" / "drhplens.css"


# ---------------------------------------------------------------------------
# Builders — valid Claim / ToolClaim / FusedAnswer objects.
# ---------------------------------------------------------------------------


def _drhp_claim(cid: str = "c_drhp01", page: int = 312) -> Claim:
    return Claim(
        claim_id=cid,
        text="Swiggy reported a consolidated loss in FY24",
        source_chunk_id="chunk-1",
        drhp_page=page,
        section="Financial Statements",
        verbatim_span="consolidated loss of INR 23,502 million",
        span_offsets=[0, 34],
        sources=[
            RetrievedChunkRef(
                chunk_id="chunk-1",
                page_start=page,
                page_end=page,
                section="Financial Statements",
                verbatim_span="consolidated loss of INR 23,502 million",
            )
        ],
    )


def _tool_claim(
    cid: str,
    tool: str,
    field: str,
    value="12.5",
) -> ToolClaim:
    return ToolClaim(
        claim_id=cid,
        text=f"the {tool} figure is {value}",
        value=value,
        source_tool=tool,
        source_record_id=f"data/{tool.split('_')[-1]}/{_DRHP_ID}.json#{field}",
    )


def _gmp_claim(cid: str = "c_gmp001", value="₹47") -> ToolClaim:
    # GMP folds into query_forecast (D-04) but resolves against the display-only
    # gmp_gap block — the field-path is what marks it as GMP (ᴳ, not ꜰ).
    return ToolClaim(
        claim_id=cid,
        text=f"the grey-market premium is {value}",
        value=value,
        source_tool="query_forecast",
        source_record_id=f"data/forecasts/{_DRHP_ID}.json#gmp_gap.gmp_spread.low",
    )


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _RecordingSt:
    """Minimal Streamlit stub recording every markdown body + expander label."""

    def __init__(self) -> None:
        self.emitted: list[str] = []
        self.expanders: list[str] = []

    def markdown(self, body, unsafe_allow_html=False):
        self.emitted.append(body)

    def expander(self, label, expanded=False):
        self.expanders.append(label)
        return _NullCtx()


def _render(fused: FusedAnswer, monkeypatch) -> _RecordingSt:
    st = _RecordingSt()
    monkeypatch.setattr(fused_answer, "st", st)
    render_fused_answer(fused)
    return st


# ── (a) read-only isolation ──────────────────────────────────────────────────
def test_read_only_isolation_no_live_client():
    """The render module imports NO live-call client and makes no live call on render
    or expand (P19). Expansion reads the cached FusedAnswer object only."""
    src = inspect.getsource(fused_answer)
    tree = ast.parse(src)
    allowed = {"__future__", "html", "re", "streamlit", "agent", "ui"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    stray = imported - allowed
    assert not stray, f"ui/fused_answer.py imports outside the render-only allowlist: {stray}"

    forbidden = (
        "openai", "genai", "instructor", "groq", "qdrant",
        "GeminiModel", ".invoke(", "GRAPH", "SUPERVISOR",
        "invoke_supervisor", "invoke_with_tracing",
        "import deepeval", "from deepeval", "langgraph", "llama_index",
        "load_forecast", "load_peers", "read_text", "json.load",
    )
    for token in forbidden:
        assert token not in src, (
            f"ui/fused_answer.py must not reference {token!r} "
            f"(render-only: reads the cached answer object, no live call)."
        )


# ── (b) C2 markers — doc numbered, tool lettered ─────────────────────────────
def test_drhp_claim_numbered_tool_claim_lettered():
    """A DRHP Claim → a numbered marker; a forecast ToolClaim → the lettered ꜰ marker.
    Doc vs data is distinguishable at a glance (the honesty payoff)."""
    fused = FusedAnswer(
        answer_prose="Losses narrowed {{c_drhp01}}; the model's low band is {{c_fcst01}}.",
        claims=[_drhp_claim(), _tool_claim("c_fcst01", "query_forecast", "interval.low_pct")],
    )
    html_out, doc_map = render_fused_prose(fused)
    assert doc_map == {"c_drhp01": 1}
    # numbered DRHP marker
    assert 'class="drhp-prov drhp-prov--doc"' in html_out
    assert 'data-claim-id="c_drhp01"' in html_out
    assert ">1</sup>" in html_out
    # lettered forecast marker
    assert 'class="drhp-prov drhp-prov--tool"' in html_out
    assert 'data-claim-id="c_fcst01"' in html_out
    assert "ꜰ</sup>" in html_out
    # one cohesive prose-first paragraph in a single wrapper
    assert html_out.startswith('<div class="drhp-fused">')
    assert html_out.count('<div class="drhp-fused">') == 1


def test_distinct_tool_markers_per_source():
    """Peers → ᴾ, GMP → ᴳ, red-flags → ᴿ — each source glyph is distinct."""
    fused = FusedAnswer(
        answer_prose="{{c_peer01}} {{c_gmp001}} {{c_rf0001}}",
        claims=[
            _tool_claim("c_peer01", "query_peers", "peers[0].pe"),
            _gmp_claim("c_gmp001"),
            _tool_claim("c_rf0001", "query_redflags", "rpt_total"),
        ],
    )
    html_out, _ = render_fused_prose(fused)
    assert "ᴾ</sup>" in html_out
    assert "ᴳ</sup>" in html_out
    assert "ᴿ</sup>" in html_out


# ── (c) FM-3 — a dropped ToolClaim renders no marker ─────────────────────────
def test_dropped_toolclaim_renders_no_marker():
    """A claim_id in the prose with no matching claim (dropped at cite-check, FM-3)
    renders NO marker — never a raw/broken citation."""
    fused = FusedAnswer(
        answer_prose="Kept {{c_keep01}}; dropped {{c_drop99}} left no marker.",
        claims=[_tool_claim("c_keep01", "query_forecast", "interval.low_pct")],
    )
    html_out, _ = render_fused_prose(fused)
    assert 'data-claim-id="c_keep01"' in html_out
    assert "c_drop99" not in html_out          # no marker, no data attr
    assert "{{c_drop99}}" not in html_out       # not left as a raw placeholder
    assert "drhp-prov" in html_out              # the kept one still renders


# ── (d) C1 — always-present provenance legend maps markers → sources ──────────
def test_provenance_legend_maps_markers_to_sources():
    fused = FusedAnswer(
        answer_prose="{{c_drhp01}} {{c_fcst01}} {{c_peer01}}",
        claims=[
            _drhp_claim(page=312),
            _tool_claim("c_fcst01", "query_forecast", "interval.low_pct"),
            _tool_claim("c_peer01", "query_peers", "peers[0].pe"),
        ],
    )
    _, doc_map = render_fused_prose(fused)
    legend = build_provenance_legend(fused, doc_map)
    assert 'class="drhp-fused-legend"' in legend
    assert "DRHP p.312" in legend
    assert "forecast · 80% PI" in legend
    assert "peers" in legend


def test_claimless_partial_has_no_empty_legend():
    """A claim-less honest partial has nothing to map — no empty legend line."""
    fused = FusedAnswer(
        answer_prose="This answer is incomplete.", claims=[], is_partial=True,
        unaddressed=["ran out of steps before finishing"],
    )
    _, doc_map = render_fused_prose(fused)
    assert build_provenance_legend(fused, doc_map) == ""


# ── (e) C3 — the honest-partial banner shows iff is_partial ───────────────────
def test_partial_banner_shows_only_when_is_partial():
    non_partial = FusedAnswer(answer_prose="Full answer.", claims=[], is_partial=False)
    assert render_partial_banner(non_partial) is None

    tool_abstain = FusedAnswer(
        answer_prose="Partial.", claims=[], is_partial=True,
        unaddressed=["no forecast band"],
    )
    banner = render_partial_banner(tool_abstain)
    assert banner is not None
    assert 'class="drhp-partial"' in banner
    assert FUSED_PARTIAL_EYEBROW in banner
    assert FUSED_PARTIAL_TOOL_ABSTAIN_BODY in banner


def test_partial_banner_budget_trip_variant():
    """A budget-trip partial (unaddressed names the step budget) uses the generic
    'stopped early' copy, not the source-specific forecast-abstain line."""
    budget = FusedAnswer(
        answer_prose="Partial.", claims=[], is_partial=True,
        unaddressed=["ran out of steps before finishing"],
    )
    banner = render_partial_banner(budget)
    assert FUSED_PARTIAL_BUDGET_BODY in banner
    assert FUSED_PARTIAL_TOOL_ABSTAIN_BODY not in banner


def test_partial_banner_renders_above_answer(monkeypatch):
    """render_fused_answer emits the banner BEFORE the prose (C3: banner above)."""
    fused = FusedAnswer(
        answer_prose="Here's what I found {{c_fcst01}}.",
        claims=[_tool_claim("c_fcst01", "query_forecast", "interval.low_pct")],
        is_partial=True, unaddressed=["ran out of steps before finishing"],
    )
    st = _render(fused, monkeypatch)
    joined = "\n".join(st.emitted)
    assert "drhp-partial" in joined
    banner_idx = next(i for i, b in enumerate(st.emitted) if "drhp-partial" in b)
    prose_idx = next(i for i, b in enumerate(st.emitted) if "drhp-fused" in b and "legend" not in b)
    assert banner_idx < prose_idx


def test_non_partial_answer_has_no_banner(monkeypatch):
    fused = FusedAnswer(
        answer_prose="Full answer {{c_fcst01}}.",
        claims=[_tool_claim("c_fcst01", "query_forecast", "interval.low_pct")],
        is_partial=False,
    )
    st = _render(fused, monkeypatch)
    assert "drhp-partial" not in "\n".join(st.emitted)


# ── (f) D-04 — GMP marker + mandatory display-only caveat ────────────────────
def test_gmp_toolclaim_carries_caveat_and_marker():
    fused = FusedAnswer(
        answer_prose="The grey-market gap is {{c_gmp001}}.",
        claims=[_gmp_claim("c_gmp001")],
    )
    html_out, _ = render_fused_prose(fused)
    assert "ᴳ</sup>" in html_out
    descriptors = build_tool_source_descriptors(fused)
    assert len(descriptors) == 1
    # The mandatory D-04 caveat is the GMP expander body (display-only framing).
    assert descriptors[0]["body"] == FUSED_GMP_CHAT_CAVEAT
    assert "never enters the model" in descriptors[0]["body"]


def test_tool_descriptors_html_escape_untrusted_value():
    """A scraped value with HTML-meaningful characters is escaped before render (XSS)."""
    fused = FusedAnswer(
        answer_prose="Peer multiple {{c_peer01}}.",
        claims=[_tool_claim("c_peer01", "query_peers", "peers[0].name",
                            value="<script>alert(1)</script>")],
    )
    descriptors = build_tool_source_descriptors(fused)
    assert "<script>" not in descriptors[0]["value"]
    assert "&lt;script&gt;" in descriptors[0]["value"]


# ── (g) no verdict colour in the appended CSS ────────────────────────────────
def test_appended_css_has_no_verdict_color_token():
    """The shipped .drhp-fused*/.drhp-prov*/.drhp-partial* block uses NO red/green/
    destructive colour token (honesty invariant — the partial banner + GMP are neutral)."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    _open = "/* === PHASE 6.3 · fused-answer additive classes"
    _close = "=== END PHASE 6.3 · fused-answer additive classes === */"
    start = css.index(_open)
    end = css.index(_close) + len(_close)
    block = css[start:end]
    # Strip CSS comments (full /* ... */ blocks) so prose (e.g. "alarm", "verdict")
    # isn't scanned — only the actual declarations are checked for a forbidden token.
    declarations = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL).lower()
    forbidden = (
        "--drhp-refusal", "red", "green", "crimson", "danger", "success",
        "destructive", "#dc2626", "#ef4444", "#f87171", "#16a34a", "#22c55e",
    )
    for token in forbidden:
        assert token not in declarations, (
            f"the fused-answer CSS block must not use the verdict token {token!r}"
        )


def test_appended_css_block_exists():
    """Guard: the sentinel-delimited additive block is actually present (so the
    no-verdict-colour test can't pass vacuously)."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    assert "PHASE 6.3 · fused-answer additive classes" in css
    assert "END PHASE 6.3 · fused-answer additive classes" in css
    for cls in (".drhp-fused", ".drhp-fused-legend", ".drhp-prov",
                ".drhp-prov--doc", ".drhp-prov--tool", ".drhp-prov-src",
                ".drhp-partial", ".drhp-partial-eyebrow"):
        assert cls in css, f"missing additive class {cls}"


# ── reuse of the existing citation expander (acceptance: not rebuilt) ────────
def test_drhp_claims_reuse_citation_expander(monkeypatch):
    """The DRHP Claim expanders route through ui.expander.render_citation_expanders
    (reused, not rebuilt) — a fused answer with a Claim produces one DRHP expander."""
    fused = FusedAnswer(
        answer_prose="Losses narrowed {{c_drhp01}}.",
        claims=[_drhp_claim(page=88)],
    )
    st = _render(fused, monkeypatch)
    # the reused expander builds the '[N] DRHP page P · Section' label
    assert any("DRHP page 88" in lbl for lbl in st.expanders)
