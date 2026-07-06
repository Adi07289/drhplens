# Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display - Pattern Map

**Mapped:** 2026-07-06
**Files analyzed:** 24 new/modified files
**Analogs found:** 22 / 24 (2 partial — external-source fetchers + historical builder)

> Every user-facing Phase 4 surface is *new records + renderers on proven rails*.
> The precompute→`data/<kind>/<id>.json`→`load_*()`→`ui/*_blocks.py` spine and the
> `{"refusal": ...}` union-discriminator codec are already solved and tested in
> `pipelines/redflag.py` + `agent/redflag_schema.py`. Copy those, do not reinvent.
> The only genuinely novel code (no clean analog) is the external HTTP fetchers
> (`peer_sources.py`, `gmp_sources.py`) and the historical panel builder.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `agent/peer_schema.py` | model/schema | transform (codec) | `agent/redflag_schema.py` | exact |
| `agent/gmp_schema.py` | model/schema | transform (codec) | `agent/redflag_schema.py` | exact |
| `pipelines/peers.py` | pipeline | batch precompute | `pipelines/redflag.py` | exact |
| `pipelines/gmp.py` | pipeline | batch precompute (isolated) | `pipelines/redflag.py` + `pipelines/snapshot.py` | role-match |
| `pipelines/peer_queries.py` | config | canned-query constants | `pipelines/redflag_queries.py` / `snapshot_queries.py` | exact |
| `pipelines/peer_sources.py` | service | file-I/O / external HTTP | `pipelines/ingest.py` (fetch loop shell) | partial |
| `pipelines/gmp_sources.py` | service | external HTTP + transform | `pipelines/ingest.py` (fetch loop shell) | partial |
| `pipelines/historical/build.py` | pipeline | batch build → artifact | `pipelines/ingest.py` + `scripts/eval_extraction.py` (`_write_report`) | partial |
| `pipelines/historical/sources.py` | service | external HTTP | (none — new) | none |
| `pipelines/historical/validate.py` | utility | transform / validation | `scripts/eval_extraction.py::_write_report` | role-match |
| `ui/format_inr.py` | utility | transform (pure fn) | `ui/catalogue.py::_format_issue_size` + `snapshot_blocks._format_fin_value` | role-match |
| `ui/snapshot_blocks.py` (ADD `render_peer_table`) | component | request-response render | `render_redflag_table` / `render_financials_table` | exact |
| `ui/snapshot_blocks.py` (ADD `render_gmp_block`) | component | request-response render | `render_idf_risk_list` / `render_split_bar` | role-match |
| `ui/copy.py` (ADD glossary + GMP + peer copy) | config | static copy | existing `ui/copy.py` constants + import-time scrubber | exact |
| `pages/02_snapshot.py` (WIRE peer + GMP blocks) | route/page | request-response | existing `_render_redflag_block` + `main()` | exact |
| `app/static/drhplens.css` (ADD peer/GMP/glossary classes) | config | stylesheet | existing `.drhp-fin-table` / `.drhp-split-bar` / `.drhp-spec-meter` | exact |
| `data/peers/<id>.json` (seed) | data | stored cache | `data/redflag/swiggy_2024_11.json` | exact |
| `data/gmp/<id>.json` (seed) | data | stored cache | `data/redflag/swiggy_2024_11.json` | exact |
| `tests/unit/test_peer_schema.py` | test | unit | `tests/unit/test_redflag_schema.py` | exact |
| `tests/unit/test_peers_precompute.py` | test | unit (monkeypatch GRAPH) | `tests/unit/test_redflag_precompute.py` | exact |
| `tests/unit/test_gmp_isolation.py` | test | unit (import-audit) | `test_cite_check::test_no_llm_judge_fallback` + `test_methodology_pane::test_no_llm_or_qdrant_import` | exact |
| `tests/unit/test_format_inr.py` | test | unit | `tests/unit/test_catalogue.py` (pure-fn asserts) | role-match |
| `tests/unit/test_historical_panel.py` | test | unit | `tests/unit/test_redflag_schema.py` (schema asserts) | role-match |
| `tests/integration/test_jugaad_data_nse.py` | test | integration (nightly) | (none — new; marker `integration`) | none |

---

## Pattern Assignments

### `agent/peer_schema.py` + `agent/gmp_schema.py` (model, transform)

**Analog:** `agent/redflag_schema.py` (read fully; also `agent/snapshot_schema.py::_dump_field`/`_load_field`).

Mirror the **union-discriminator codec** verbatim. A `PeerRecord`/`GmpRecord` is a
Pydantic `BaseModel` with a locked-key `frozenset`, a `field_validator` that rejects
unknown keys, and `to_dict`/`to_json`/`from_dict`/`from_json` methods.

**Locked-key set + rejecting-validator** (`agent/redflag_schema.py:59-69, 146-163`):
```python
REDFLAG_FIELD_KEYS: frozenset[str] = frozenset({"rpt_pct", "ofs_vs_fresh", ...})

@field_validator("fields")
@classmethod
def fields_keys_known(cls, v: dict[str, RedFlagField]) -> dict[str, RedFlagField]:
    unknown = set(v.keys()) - REDFLAG_FIELD_KEYS
    if unknown:
        raise ValueError(f"Unknown red-flag field key(s): {sorted(unknown)}; ...")
    return v
```

**The `{"refusal": ...}` discriminator codec** (`agent/redflag_schema.py:72-91`) — copy for the peer-SET value, which is `GroundedAnswer | RefusalResponse` (D4-06 empty-state IS a `RefusalResponse`, exactly like a not-disclosed red-flag field):
```python
def _dump_field_value(value: GroundedAnswer | RefusalResponse) -> dict:
    if isinstance(value, RefusalResponse):
        return {"refusal": value.model_dump()}
    return value.model_dump()

def _load_field_value(raw: dict) -> GroundedAnswer | RefusalResponse:
    if "refusal" in raw:
        return RefusalResponse.model_validate(raw["refusal"])
    return GroundedAnswer.model_validate(raw)
```

**`to_dict`/`from_dict`/`to_json` shape** (`agent/redflag_schema.py:165-213`) — `to_json` uses `json.dumps(..., indent=2, ensure_ascii=False)` for diff-reviewable committed caches. Reuse verbatim.

**Phase-4-specific delta — per-cell provenance (PEER-02, D4-05):** the peer MULTIPLES have no red-flag analog. Model each `(company, metric)` cell as a small model, e.g. `PeerCell(value: float | None = None, source: Literal["s","y","n","d"] | None = None)`. A missing cell is `PeerCell()` → renders `—`; a negative/undefined P/E carries a sentinel the UI renders as `NM`. Import `GroundedAnswer, RefusalResponse` from `agent/schemas.py` (never redefine — the `claim_id` regex `^c_[a-z0-9]{6,16}$` and `Claim` contract are cross-phase locked, `agent/schemas.py:79-83`).

**GMP schema isolation (D4-03):** `agent/gmp_schema.py` must import ONLY from `pydantic` and stdlib — NOT from `agent.schemas` if that pulls model code, and NEVER from any forecast module. Model as `GmpRecord(drhp_id, computed_at, quotes: list[GmpQuote], as_of)`, `GmpQuote(source: str, value: float, as_of: str)`. Spread (`low`/`high`/`n`) is derived at render, or stored precomputed.

---

### `pipelines/peers.py` (pipeline, batch precompute) — PEER-01/PEER-02

**Analog:** `pipelines/redflag.py` (read fully).

**Allow-list-gated path formation** (`pipelines/redflag.py:49, 70-104`) — copy verbatim, this is the T-02-V5/T-03-01 path-traversal control (V4 Access Control in the security domain):
```python
PEERS_DIR: Path = Path(__file__).parent.parent / "data" / "peers"

def load_peers(drhp_id: str) -> PeerRecord:
    path = _peers_path(drhp_id)              # gate happens INSIDE
    if not path.exists():
        raise FileNotFoundError(f"No peer cache for drhp_id={drhp_id!r} at {path}")
    return PeerRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

def _peers_path(drhp_id: str) -> Path:
    if not is_known_drhp_id(drhp_id):        # BEFORE the path string is built
        raise ValueError(f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path.")
    return PEERS_DIR / f"{drhp_id}.json"
```

**Peer-SET extraction reuses the agent canned-query loop** (`pipelines/redflag.py:129-243`). Gate the id up front (lines 157-162), then `from agent.graph import GRAPH` (deferred import, line 164) and `GRAPH.invoke({"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0})`. The graph's `RefusalResponse` return IS the D4-06 honest empty-state — store it as the peer-SET value, never fabricate. NO new LLM path, NO "peer mode" in the graph.

**Per-cell fetch orchestration (the Phase-4 delta):** after the SET is extracted, loop the named peers and call `pipelines/peer_sources.py` in source-priority order (screener→yfinance→NSE), recording which source supplied each cell. Keep this at **precompute time only** (D3-17 / P16) — never in `load_peers` or a page function.

**Per-IPO failure isolation + CLI** (`pipelines/redflag.py:314-361`) — copy the Typer `precompute-one` / `precompute-all` commands with the per-IPO `try/except` that logs and continues (P14 posture).

**`write` kwarg for offline tests** (`pipelines/redflag.py:129, 147-148, 238-241`): `precompute_peers(drhp_id, *, write: bool = True)`; tests pass `write=False`.

---

### `pipelines/gmp.py` (pipeline, batch precompute — ISOLATED) — GMP-01/GMP-02

**Analog:** `pipelines/redflag.py` (path-gate + CLI) + `pipelines/snapshot.py` (simpler no-graph precompute shell, `snapshot.py:1-63`).

Same `GMP_DIR` + `load_gmp` + `_gmp_path` allow-list gate as peers above. GMP does NOT use the agent graph — it is `scrape A,B,C → [{source, value, as_of}] → spread → data/gmp/<id>.json`.

**Hard isolation invariant (D4-03/GMP-02):** this module and `agent/gmp_schema.py` import NOTHING from any forecast/feature/model package. Pinned by `tests/unit/test_gmp_isolation.py` (below). Do not import `xgboost`, `mapie`, `sklearn`, `pipelines.features`, or anything the Phase-5 forecaster will import.

**Empty/single-source states (D4-06 GMP variant):** most catalogue IPOs already listed → GMP is legitimately absent. Model absent-GMP as first-class (`quotes == []` → UI renders the honest "No GMP is being reported…" note), and single-source (`len(quotes) == 1` → "Only one source reported"). Never fabricate a number or a zero.

---

### `pipelines/peer_queries.py` (config, canned-query constants)

**Analog:** `pipelines/redflag_queries.py` (read fully) + `pipelines/snapshot_queries.py`.

A module-level `dict[str, str]` of versioned queries, keys LOCKED to the schema's `frozenset` (kept in sync, enforced by the schema validator). Header comment explains each string is run once per `drhp_id` through the existing graph and edits are reviewable. For PEER-01 a single canned query suffices:
```python
# pipelines/peer_queries.py  (mirror redflag_queries.py:25-57 style)
PEER_SET_QUERY = (
    "In the 'Basis for Issue Price' or 'Comparison with Listed Industry Peers' "
    "section, which listed companies does the company name as its peers, and on "
    "what DRHP page? List each peer company name exactly as disclosed."
)
```

---

### `pipelines/peer_sources.py` + `pipelines/gmp_sources.py` (service, external HTTP) — PARTIAL analog

**No exact analog exists** — these are the genuinely new fetchers. The nearest shell is `pipelines/ingest.py` (the per-IPO fetch/parse loop with `requests-cache`, `tenacity`, per-item failure isolation, and `rich` progress). Reuse the project stack, do not hand-roll (RESEARCH §Don't Hand-Roll): `requests-cache` for HTTP caching, `tenacity` for backoff, `beautifulsoup4`+`lxml` for HTML parse, `rapidfuzz` (already a Phase-3 dep in `pipelines/risk_idf.py`) for peer-name→ticker matching.

**Security controls to carry (V5 Input Validation):** scrape only hard-coded source hostnames (no URL derived from user/DRHP input — SSRF control); treat every scraped string as untrusted → the renderer HTML-escapes it (see `ui/chip.py`/`ui/expander.py` escape pattern below). Return `None` for a missing/zero ratio (P15 — never let yfinance `0.0`/`NaN` masquerade as a real value).

---

### `ui/format_inr.py` (utility, pure transform) — UI-04/D4-07

**Analog to FIX (FLAG-FORMAT):** `ui/catalogue.py::_format_issue_size` (`ui/catalogue.py:37-41`) and `snapshot_blocks._format_fin_value` (`ui/snapshot_blocks.py:180-191`).

The **latent Western-grouping bug** to fix (`ui/catalogue.py:37-41`):
```python
def _format_issue_size(issue_size_cr: int | None) -> str:
    if issue_size_cr is None:
        return "Issue size not disclosed"
    return f"₹{issue_size_cr:,} cr"          # BUG: ₹1,234,567 (Western), wrong for India
```
And the second bare-`:,` call site (`ui/snapshot_blocks.py:184-190`):
```python
if value is None:
    return f'<span aria-label="Not disclosed in this DRHP">—</span>'
...
if value < 0:
    return f"(₹{abs(value):,.0f} cr)"        # Western grouping again
return f"₹{value:,.0f} cr"
```

**Build ONE `format_inr(amount) -> str`** with Indian grouping (last 3 digits, then groups of 2) + auto-scaled lakh/crore + `None → "—"` sentinel + negatives-in-parens (RESEARCH §Code Examples has the reference algorithm). Then **refactor both call sites above to call it** — do not duplicate grouping (D4-07 = ONE utility). The `—` sentinel and no-red-for-negatives convention already match `_format_fin_value` (`snapshot_blocks.py:184, 189`), so behaviour is preserved.

**Grep to enumerate every ₹ call site to retrofit (run in plan):** `grep -rn "₹\|:,\|cr\"" ui/ pages/`. Adoption pinned by `tests/unit/test_format_inr_adoption.py`.

`tabular-nums` is applied by CSS, not the utility (matches `.drhp-fin-table { font-variant-numeric: tabular-nums; }`, `drhplens.css:470`).

---

### `ui/snapshot_blocks.py` — ADD `render_peer_table` (component) — PEER-01/02

**Analog:** `render_redflag_table` (`ui/snapshot_blocks.py:329-395`) + `render_financials_table` (`ui/snapshot_blocks.py:194-241`).

**HARD RULE — the Streamlit white-bar lesson** (`ui/snapshot_blocks.py:345-353`, the exact comment): use `with st.container(border=True):` as the card wrapper, then a SINGLE self-contained `st.markdown` for the table HTML. NEVER open `<div>` in one `st.markdown` and close in another (renders an empty white bar).
```python
with st.container(border=True):          # the card — NOT a split <div>
    st.markdown(f'<h2 class="drhp-snapshot-block-heading">{_html.escape(heading)}</h2>',
                unsafe_allow_html=True)
    st.caption(subline)
    ...
```

**Table HTML pattern — reuse `.drhp-fin-table-wrap` overflow + sticky-left column** (`ui/snapshot_blocks.py:226-241`; CSS at `drhplens.css:463-486`). Axis per UI-SPEC R-2: rows = companies, columns = `Company · P/E · P/B · EV/EBITDA · ROE`, real `<table>` with `<th scope="col">`/`<th scope="row">`:
```python
table_html = (
    '<div class="drhp-fin-table-wrap"><table class="drhp-peer-table">'
    f'<thead><tr><th scope="col">Company</th>{header_cells}</tr></thead>'
    f'<tbody>{"".join(body_rows)}</tbody>'
    '</table></div>'
)
st.markdown(table_html, unsafe_allow_html=True)
```

**Peer-SET citation reuses the UNCHANGED chip + expander renderers** (`ui/chip.py::render_answer_with_chips`, `ui/expander.py::render_citation_expanders`; see `_render_expanders` at `snapshot_blocks.py:54-69`). This is the ONLY accent element in the block (D4-04). Do NOT build a new citation shape.

**Per-cell provenance superscript (R-3):** render inline in the cell HTML as `<sup class="drhp-provenance-flag" aria-label="source: screener.in">s</sup>` — muted, unfilled, distinct from the accent filled chip. Cell edge cases mirror `_format_fin_value` (`snapshot_blocks.py:180-191`): missing → `—` + aria-label; negative → parens same colour; `NM` for undefined P/E.

**Honest empty-state (D4-06)** reuses `_render_not_disclosed` (`snapshot_blocks.py:46-51`) — the `.drhp-not-disclosed` note, copy `This DRHP disclosed no listed-peer comparison.`

**XSS control (V5):** every scraped peer name goes through `_html.escape(..., quote=True)` before interpolation — the escape-then-interpolate contract already used throughout this module and in `ui/chip.py:75-79`, `ui/catalogue.py:61-66`.

---

### `ui/snapshot_blocks.py` — ADD `render_gmp_block` (component) — GMP-01/02

**Analog:** `render_split_bar` (`ui/snapshot_blocks.py:118-166`) for the monochrome range/track grammar + `render_idf_risk_list` (`snapshot_blocks.py:413-486`) for the block structure.

**Monochrome range strip** — copy the `render_split_bar` grammar (single self-contained `st.markdown`, `role="img"` + text `aria-label` so the spread is never position-only, WCAG 1.4.1), but with NO accent (the split bar uses accent for OFS; GMP uses only greys):
```python
# mirror snapshot_blocks.py:158-166 — one self-contained markdown, role=img + aria
st.markdown(
    f'<div class="drhp-gmp-range" role="img" '
    f'aria-label="{_html.escape(aria, quote=True)}">'
    f'...one muted tick per aggregator positioned by inline left:%...'
    f'</div>',
    unsafe_allow_html=True,
)
```

**Wrap in `st.container(border=True)`** (the same white-bar rule) and put the "What is GMP? Why we don't trust it" explainer in an inherited `st.expander(..., expanded=False)` with a **unique `key`** (avoids `StreamlitDuplicateElementId`; the methodology pane already passes `key=f"redflag_{field_key}"`, `snapshot_blocks.py:387-393`). All ₹ values via `format_inr`. Absent/single-source/error states per the UI-SPEC states table.

---

### `ui/copy.py` — ADD glossary + GMP + peer copy (config)

**Analog:** existing `ui/copy.py` (read the header + the import-time scrubber block, `ui/copy.py:1-14, 410-479`).

Add the 8 glossary definitions, GMP caveat/disclosure body, peer heading/sub-line/legend, and empty/error states as module-level `str` constants — the import-time scrubber loop (`ui/copy.py:474-478`) auto-covers every new `str`. Verbatim strings are in the UI-SPEC §Copywriting Contract. **The `sell` stem is scrubber-flagged** (`ui/copy.py` L8 note) — the OFS/GMP definitions are pre-worded to avoid it ("shares offered by existing shareholders"). Format-string templates (with `{...}`) get sample-substituted before scrubbing (`ui/copy.py:451-472`); add any new placeholder names (e.g. `low`, `high`, `source`, `value`) to `_SAMPLE_FORMAT_VALUES` (`ui/copy.py:426-448`).

---

### `pages/02_snapshot.py` — WIRE peer + GMP blocks (route)

**Analog:** the existing `main()` + `_render_redflag_block` (`pages/02_snapshot.py:95-119, 122-228`).

**Cache-read posture — copy the redflag block's try/except** (`pages/02_snapshot.py:163-176`): `load_peers`/`load_gmp` inside try/except → `FileNotFoundError` = missing/empty-state, other `Exception` = amber `.drhp-refusal` banner (NOT red), never an unhandled exception. The `drhp_id` is already allow-list-validated at the top of `main()` (`pages/02_snapshot.py:126`) — the same guard covers the new loads.

**IA insertion (UI-SPEC §IA):** peer block after Key Financials (block 7); GMP block MUST be the last read block before the Q&A `2xl` divider (block 10, `pages/02_snapshot.py:221-226` is where the divider is emitted — insert GMP immediately above it). Import the two new renderers alongside the existing `from ui.snapshot_blocks import (...)` (`pages/02_snapshot.py:41-49`).

---

### `app/static/drhplens.css` — ADD peer/GMP/glossary classes (config)

**Analog:** `.drhp-fin-table*` (`drhplens.css:463-509`), `.drhp-split-bar*` (`drhplens.css:419-461`), `.drhp-spec-meter` grammar, and the four `@media` breakpoints (`drhplens.css:249-330`).

Single stylesheet (FLAG-2 — no inline `<style>` from other modules). New classes consume the inherited `--drhp-*` tokens (`drhplens.css:9-27`) — NO new hex, NO red/green. `.drhp-peer-table` mirrors `.drhp-fin-table` (`tabular-nums`, sticky-left first column `position: sticky; left: 0`, `surface-secondary` header + zebra, `drhplens.css:467-509`). `.drhp-gmp-range`/`.drhp-gmp-tick` mirror the `.drhp-split-bar` monochrome track but with muted ticks and no accent. `.drhp-glossary`/`.drhp-glossary-pop` are the pure-CSS `:hover`/`:focus`/`:focus-within` popover (RESEARCH §Code Examples; UI-SPEC R-1) with the inherited 44×44 `::before` tap enlarger (same mechanism as `.drhp-cite::before`, `drhplens.css:75`).

---

### Test files

| Test file | Analog | What to copy |
|-----------|--------|--------------|
| `tests/unit/test_peer_schema.py` | `tests/unit/test_redflag_schema.py` | round-trip `to_dict`/`from_dict`, `{"refusal":...}` codec, unknown-key rejection, per-cell None/NM cases |
| `tests/unit/test_peers_precompute.py` | `tests/unit/test_redflag_precompute.py` (read `:1-90`) | monkeypatch `agent.graph.GRAPH.invoke`; `KNOWN_DRHP_ID = "swiggy_2024_11"`; grounded-state / refusal-state builders; `::test_path_gate` asserts `ValueError` on unknown id |
| `tests/unit/test_gmp_isolation.py` | `test_cite_check::test_no_llm_judge_fallback` (`:141-163`) + `test_methodology_pane::test_no_llm_or_qdrant_import` (`:211-221`) | the `inspect.getsource` / `ast` import-audit — see Shared Patterns below |
| `tests/unit/test_format_inr.py` | pure-fn asserts (`test_catalogue.py` style) | the RESEARCH test-case table: `100000→₹1 lakh`, `1250000→₹12.5 lakh`, `45600→₹45,600`, `None→—`, `-1234→(₹1,234)` |
| `tests/unit/test_historical_panel.py` | `test_redflag_schema.py` (schema asserts) | `status` column present, NaN-not-drop survivorship, ~7% median-baseline flag |
| `tests/integration/test_jugaad_data_nse.py` | (none — new) | marker `integration`; smoke NSE bhavcopy + a listing-day candle; GitHub Actions scheduled |

---

## Shared Patterns

### Allow-list-gated cache path (V4 Access Control, T-02-V5 / T-03-01)
**Source:** `data/catalogue_loader.py::is_known_drhp_id` (`:75-88`); usage in `pipelines/redflag.py::_redflag_path` (`:92-104`).
**Apply to:** `pipelines/peers.py`, `pipelines/gmp.py`, and the `pages/02_snapshot.py` reads.
Gate `drhp_id` through `is_known_drhp_id()` BEFORE forming any `data/<kind>/<drhp_id>.json` string. A non-allow-listed id raises `ValueError` — no path is built. This is the path-traversal control; copy it verbatim, do not weaken it.

### Union-discriminator cache codec (`{"refusal": ...}`)
**Source:** `agent/redflag_schema.py:72-91, 165-213` (identical to `agent/snapshot_schema.py:39-50`).
**Apply to:** `agent/peer_schema.py` (peer-SET value), `agent/gmp_schema.py` if any field is `GroundedAnswer | RefusalResponse`.
A value dict with a `"refusal"` key → `RefusalResponse`; anything else → `GroundedAnswer` (always carries `answer_prose`). `to_json` = `json.dumps(..., indent=2, ensure_ascii=False)` for diff-reviewable committed caches.

### Escape-then-interpolate for all untrusted strings (V5, XSS control)
**Source:** `ui/chip.py:75-79` (escape prose before chip substitution), `ui/expander.py:77-83` (escape every snippet field), `ui/catalogue.py:61-66` (`html.escape(..., quote=True)`).
**Apply to:** every scraped peer name, GMP source label, and any DRHP-derived string rendered via `unsafe_allow_html`. Scraped HTML is untrusted input — `_html.escape(s, quote=True)` before it touches a markdown string.

### GMP module-isolation import-audit (D4-03 / GMP-02) — the pin
**Source:** `tests/unit/test_cite_check.py::test_no_llm_judge_fallback` (`:141-163`, AST-based) and `tests/unit/test_methodology_pane.py::test_no_llm_or_qdrant_import` (`:211-221`, `inspect.getsource` substring). Both are proven substring/import-audit patterns.
**Apply to:** `tests/unit/test_gmp_isolation.py`.
```python
import inspect, pipelines.gmp, agent.gmp_schema
def test_gmp_module_imports_no_model_code():
    for mod in (pipelines.gmp, agent.gmp_schema):
        src = inspect.getsource(mod)
        for forbidden in ("xgboost", "mapie", "forecast", "sklearn", "pipelines.features"):
            assert forbidden not in src, f"GMP module must not reference {forbidden} (D4-03/GMP-02)"
```
(Phase 5 owns the reverse audit: the forecaster must not import `pipelines.gmp`.)

### Import-time copy scrubber (TRUST-03)
**Source:** `ui/copy.py:410-479` — the module walks its own `vars()`, sample-substitutes format templates, and asserts every `str` passes `compliance.scrubber.scrub`.
**Apply to:** all Phase 4 glossary/GMP/peer/empty/error copy — landing a constant in `ui/copy.py` auto-enrols it. Add new template placeholders to `_SAMPLE_FORMAT_VALUES` (`:426-448`). Avoid the `sell` stem.

### Streamlit container card + unique expander key (Phase 3 white-bar lesson)
**Source:** `ui/snapshot_blocks.py:345-353` (the verbatim explanatory comment) + `:387-393` (unique `key=`).
**Apply to:** `render_peer_table`, `render_gmp_block`. `with st.container(border=True):` as the card; single self-contained `st.markdown` for HTML; every `st.expander` gets a unique `key`.

### Per-IPO failure isolation in precompute-all (P14)
**Source:** `pipelines/redflag.py::precompute_all` (`:330-361`) — `try/except` per IPO logs and continues, never aborts the batch.
**Apply to:** `pipelines/peers.py`, `pipelines/gmp.py`, `pipelines/historical/build.py` fetch loops.

---

## No Analog Found

Files with no close match in the codebase (planner should lean on RESEARCH.md's stack + examples):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pipelines/historical/sources.py` | service | external HTTP | No chittorgarh/SEBI-issuer-side/jugaad-data fetcher exists yet; `pipelines/ingest.py` gives only the HTTP-loop shell (`requests-cache`/`tenacity`/`rich`), not the survivorship-corrected panel logic. |
| `tests/integration/test_jugaad_data_nse.py` | test | integration | No `tests/integration/` NSE smoke test exists; new nightly `integration`-marked test per the ROADMAP Wave-0 jugaad-data validation flag. |

**Partial analogs** (shell exists, core logic new): `pipelines/peer_sources.py`, `pipelines/gmp_sources.py` (fetch-loop shell from `ingest.py`; the external-source parsing is new and fragile — this IS the phase's real risk per RESEARCH), and `pipelines/historical/build.py` / `validate.py` (artifact-write shell from `scripts/eval_extraction.py::_write_report` at `:212-300`; parquet/CSV commit + ~7% median sanity-flag logic is new).

---

## Metadata

**Analog search scope:** `pipelines/`, `agent/`, `ui/`, `pages/`, `data/`, `tests/unit/`, `scripts/`, `app/static/`
**Files scanned:** `redflag.py`, `redflag_schema.py`, `redflag_queries.py`, `snapshot.py`, `snapshot_schema.py`, `snapshot_queries.py`, `schemas.py`, `catalogue_loader.py`, `ui/catalogue.py`, `ui/chip.py`, `ui/expander.py`, `ui/snapshot_blocks.py`, `ui/copy.py`, `pages/02_snapshot.py`, `app/static/drhplens.css`, `pipelines/ingest.py`, `scripts/eval_extraction.py`, `tests/unit/test_cite_check.py`, `tests/unit/test_methodology_pane.py`, `tests/unit/test_redflag_precompute.py` (20 analog files read)
**Pattern extraction date:** 2026-07-06
</content>
</invoke>
