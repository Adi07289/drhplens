# Phase 5: Calibrated Listing-Day Forecaster - Pattern Map

**Mapped:** 2026-07-15
**Files analyzed:** 24 new/modified (8 forecast pipeline, 3 historical-source edits, 1 schema, 1 render helper, 2 page edits, copy + CSS, 9 tests, model-card artifact, pyproject)
**Analogs found:** 18 with strong analog / 24 (6 are genuinely new modeling code — see §No Analog Found)

> **Read-only note:** this document maps new files to existing patterns. The
> modeling half (MAPIE CQR, walk-forward loop, DM test, SHAP/matplotlib) has NO
> in-repo analog — the codebase has zero modeling code today. Those files copy
> from `05-RESEARCH.md` §Pattern 1/2/4 + §Code Examples, not from a repo file.
> Everything else (cache writer/loader, record schema, allow-list gate, render
> block, copy, CSS, isolation/schema/precompute tests, source fetchers) has a
> tight, tested analog cited below with exact line numbers.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `agent/forecast_schema.py` (NEW) | model/schema | transform | `agent/gmp_schema.py` | exact |
| `pipelines/forecast/__init__.py` — `load_forecast()` (NEW) | service/loader | file-I/O (cache read) | `pipelines/gmp.py` `load_gmp`/`_gmp_path` | exact |
| `pipelines/forecast/precompute.py` — CLI writer (NEW) | service/pipeline | batch (write cache) | `pipelines/gmp.py` `precompute_gmp`+CLI / `pipelines/snapshot.py` | exact |
| `pipelines/forecast/model.py` — XGB-quantile + MAPIE CQR (NEW) | service (model) | transform | **none** (RESEARCH §Pattern 1) | no-analog |
| `pipelines/forecast/walkforward.py` — as-of-T0 loop (NEW) | service (model) | batch/transform | **none** (RESEARCH §Pattern 2) | no-analog |
| `pipelines/forecast/baselines.py` — 4 baselines + DM (NEW) | service (model) | transform | **none** (RESEARCH §Pattern 4, Code Examples) | no-analog |
| `pipelines/forecast/diagnostics.py` — coverage/MAE/RMSE, plots, SHAP (NEW) | service (model) | transform → file-I/O (PNG) | partial: `validate.py` for metric-note posture | partial |
| `pipelines/features/__init__.py` — FEATURE_SPECS + available_at rules (NEW) | config/schema | transform | `pipelines/historical/__init__.py` (PANEL_COLUMNS/STATUS_VALUES) | role-match |
| `pipelines/features/build.py` — feature matrix + leakage audit (NEW) | service (model) | transform | `pipelines/historical/__init__.py` `assemble_panel` (typed coerce, replace-with-NaN) | role-match |
| `pipelines/historical/sources.py` (MODIFY — D5-04) | service (fetcher) | request-response (scrape) | itself (existing `fetch_*` + `ALLOWED_HOSTS`) | exact (in-place) |
| `pipelines/historical/build.py` (MODIFY — two-source merge) | service (pipeline) | batch | itself (`build_panel`, `derive_status`) | exact (in-place) |
| `pipelines/historical/validate.py` (REUSE — run on real panel) | utility | transform | itself | exact (reuse) |
| `data/forecasts/<drhp_id>.json` (NEW cache kind) | data/cache | file-I/O | `data/gmp/<drhp_id>.json` shape | exact |
| `ui/forecast_block.py` — cache-only render (NEW) | component (render) | request-response (read) | `ui/snapshot_blocks.py` `render_gmp_block`+`_render_gmp_spread` | exact |
| GMP-implied-return conversion helper (NEW, display layer) | utility | transform | `ui/format_inr.py` + `ui/snapshot_blocks.py` GMP block | role-match |
| `pages/02_snapshot.py` (MODIFY — insert forecast block) | route/page | request-response | itself (`_render_peer_block` guard + wiring) | exact (in-place) |
| `pages/01_methodology.py` (MODIFY — model-card section) | route/page | request-response | itself (section-head + table/card grammar) | exact (in-place) |
| `ui/copy.py` (MODIFY — new forecast strings) | config/copy | n/a | itself (constant block + import-time scrubber loop) | exact (in-place) |
| `app/static/drhplens.css` (MODIFY — `.drhp-forecast-*`) | config/styles | n/a | itself (single CSS source; `.drhp-gmp-*`/`.drhp-split-bar` classes) | exact (in-place) |
| `model_card/MODEL_CARD.md` + PNGs (NEW artifact) | doc/artifact | file-I/O | partial: `data/historical/README.md` writer in `build.py` | partial |
| `tests/unit/test_forecast_isolation.py` (NEW) | test | n/a | `tests/unit/test_gmp_isolation.py` | exact |
| `tests/unit/test_forecast_schema.py` (NEW) | test | n/a | `tests/unit/test_gmp_schema.py` | exact |
| `tests/unit/test_forecast_block_render.py` / `..._metrics` / `..._cqr_interval` / `..._baselines_dm` / `..._walkforward_no_lookahead` / `..._features_available_at` (NEW) | test | n/a | `tests/unit/test_gmp_precompute.py` (monkeypatch posture) | role-match |
| `tests/unit/test_historical_panel.py` (EXTEND) | test | n/a | itself | exact (in-place) |
| `pyproject.toml` (MODIFY — add deps) | config | n/a | itself | exact (in-place) |

---

## Pattern Assignments

### `agent/forecast_schema.py` — the `ForecastRecord` cache schema (model/schema, transform)

**Analog:** `agent/gmp_schema.py` (read in full) — a pydantic `BaseModel` record
with `to_dict`/`to_json`/`from_dict`/`from_json` codec, first-class empty/edge
states as `@property`, and a module-level ISOLATION docstring. The forecast
record is flatter (a single `interval` dict + `metrics` dict per RESEARCH
§Forecast Record Schema) but uses the identical codec + abstain-as-first-class
posture.

**Codec + on-disk shape pattern** (`agent/gmp_schema.py:118-159`):
```python
class GmpRecord(BaseModel):
    drhp_id: str
    computed_at: str
    quotes: list[GmpQuote] = []
    as_of: str

    @property
    def is_absent(self) -> bool:          # first-class empty state (mirror -> `abstain`)
        return len(self.quotes) == 0

    def to_dict(self) -> dict: ...          # flat on-disk dict
    def to_json(self) -> str:               # json.dumps(..., indent=2, ensure_ascii=False)
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    @classmethod
    def from_dict(cls, raw: dict) -> "GmpRecord": ...
    @classmethod
    def from_json(cls, text: str) -> "GmpRecord":
        return cls.from_dict(json.loads(text))
```

**Isolation-docstring pattern to copy verbatim in intent** (`agent/gmp_schema.py:30-40`):
"this module imports ONLY pydantic + stdlib. It pulls in NO modelling library…
pinned by tests/unit/test_gmp_isolation.py." For the forecast RECORD schema the
mirror is: imports only pydantic + stdlib, NO GMP/model objects, pinned by the
new `test_forecast_isolation.py` (render-side) — the record is the isolation
boundary between offline model and cache-only render.

**Forecast-specific fields** (from RESEARCH §Forecast Record Schema, lines 464-484):
`model_version`, `as_of_listing_date`, `out_of_sample`/`walk_forward` bools,
`abstain`+`abstain_reason` (`insufficient_history`|`out_of_support`|`interval_too_wide`),
`interval:{low_pct,high_pct,median_pct,width_pts}`, `sector`, and a GLOBAL
`metrics:{coverage_empirical,mae_pts,backtest_window,n,per_year_rmse}`. Keep
`median_pct` a Small-annotation field, never a headline (UI-SPEC P21).

---

### `pipelines/forecast/__init__.py` — `load_forecast(drhp_id)` (service/loader, file-I/O)

**Analog:** `pipelines/gmp.py:57-92` (`load_gmp` + `_gmp_path`) — verbatim
allow-list-gated cache read. RESEARCH §"Forecast record write" (lines 448-462)
already sketches this exact mirror.

**Loader + path-gate pattern** (`pipelines/gmp.py:57-92`):
```python
def load_gmp(drhp_id: str) -> GmpRecord:
    path = _gmp_path(drhp_id)                       # gate FIRST
    if not path.exists():
        raise FileNotFoundError(f"No GMP cache found for drhp_id={drhp_id!r} at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GmpRecord.from_dict(raw)

def _gmp_path(drhp_id: str) -> Path:
    if not is_known_drhp_id(drhp_id):               # T-04-04-PATH allow-list gate
        raise ValueError(f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path …")
    return GMP_DIR / f"{drhp_id}.json"
```
`GMP_DIR: Path = Path(__file__).parent.parent / "data" / "gmp"` (`pipelines/gmp.py:49`)
→ for forecast, `FORECASTS_DIR = Path(__file__).resolve().parents[2] / "data" / "forecasts"`.
`is_known_drhp_id` comes from `data/catalogue_loader.py:75-88` (the V5 allow-list;
read in full). **Reuse it before ANY forecast path is formed** — same gate the
render side already applies at `pages/02_snapshot.py:190`.

---

### `pipelines/forecast/precompute.py` — the record writer + Typer CLI (service/pipeline, batch)

**Analog:** `pipelines/gmp.py:110-224` (`precompute_gmp` + `precompute-one`/
`precompute-all` CLI) and `pipelines/snapshot.py:281-319`. The forecast writer
differs (it consumes the offline walk-forward output rather than scraping), but
the **write path, allow-list gate, and per-IPO failure isolation are identical.**

**Write pattern** (`pipelines/gmp.py:134-170`):
```python
if not is_known_drhp_id(drhp_id):                   # gate up front, before any work
    raise ValueError(f"Unknown drhp_id={drhp_id!r}; refusing to pre-compute …")
...
record = GmpRecord(drhp_id=drhp_id,
                   computed_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"), ...)
if write:
    path = _gmp_path(drhp_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.to_json(), encoding="utf-8")
return record
```

**Per-IPO failure isolation loop** (`pipelines/gmp.py:203-223`, identical in
`snapshot.py:292-318` and `redflag.py:330-361`):
```python
for ipo in load_catalogue():
    try:
        record = precompute_...(ipo.drhp_id)
        results.append((ipo.drhp_id, "ok"))
    except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation (P14)
        console.print(f"  [red]FAILED: {exc}[/red]")
        results.append((ipo.drhp_id, "failed"))
```
Use `typer.Typer(...)` + `rich.console.Console()` (`pipelines/gmp.py:46-47`).
**CODE-NOW-DEFER**: the real training run is offline/deferred; the CLI must be
unit-testable with the model output monkeypatched, exactly as `snapshot.py`/
`gmp.py` defer their live runs (docstrings at `snapshot.py:11-14`, `gmp.py:23-27`).

---

### `pipelines/features/__init__.py` + `build.py` — feature matrix + `available_at` gate (config/schema + model, transform)

**Analog:** `pipelines/historical/__init__.py` (read in full) — the column-contract
+ typed-frame + replace-with-NaN pattern. Features are a NEW concern, but the
**declare-columns-as-a-constant, validate-each-row, never-drop** grammar copies directly.

**Column-contract-as-constant** (`pipelines/historical/__init__.py:41-73`):
```python
STATUS_VALUES: frozenset[str] = frozenset({...})    # taxonomy as a frozenset
PANEL_COLUMNS: tuple[str, ...] = ("issuer", "issue_date", ..., "listing_day_return", "status")
PANEL_DTYPES: dict[str, str] = {"issuer": "string", "listing_day_return": "float64", ...}
```
→ mirror as `FEATURE_SPECS`: each feature name → `(dtype, available_at_rule)`.
The `available_at <= T0` leakage rule (D5-08, RESEARCH §Pattern 3 table lines
311-318) is the feature-layer analog of `STATUS_VALUES` validation.

**Validate-each-row-or-raise + replace-with-NaN** (`__init__.py:116-172`):
```python
for i, row in enumerate(rows):
    status = row.get("status")
    if status not in STATUS_VALUES:
        raise ValueError(f"Row {i} … has invalid status={status!r}; …")  # never coerce a survivor
    ...
    supplied_return = _to_float_or_nan(row.get("listing_day_return"))
    listing_return = supplied_return if not math.isnan(supplied_return) \
        else compute_listing_day_return(issue_price, listing_close)     # NaN retained, never dropped
```
→ the feature builder asserts every feature's `available_at <= T0` (raise on
violation, the leakage analog of the invalid-status raise) and keeps a missing
feature as NaN. `compute_listing_day_return` (`__init__.py:81-98`) is the target
column — consume it directly, do not recompute.

**R²>0.5 leakage alarm** (RESEARCH §Pattern 3, line 319) has NO code analog but
the **plain-text divergence-flag posture** to copy is `validate.sanity_check_median`
(`pipelines/historical/validate.py:40-107`): compute a statistic, return
`(value, flag_text_or_None)`, surface the flag verbatim on `/methodology`. Mirror
that shape for the R²>0.5 alarm and the coverage/MAE report.

---

### `pipelines/historical/sources.py` — MODIFY for D5-04 (service/fetcher, request-response)

**Analog:** the file itself (read in full). `fetch_chittorgarh_index`
(`sources.py:190-228`) is the **dead selector to retire** (`soup.find("table")` →
0 rows; site is Next.js now). Repoint to NSE past-issues (Source A) + a SEBI/
withdrawn fetcher (Source B), keeping every existing control.

**SSRF allow-list — EXTEND, don't bypass** (`sources.py:38-44`, `_check_host` at 78-85):
```python
ALLOWED_HOSTS: frozenset[str] = frozenset({
    "www.chittorgarh.com", "www.sebi.gov.in", "nsearchives.nseindia.com",
})
# D5-04: ADD "www.nseindia.com" (past-issues JSON) + confirm the SEBI filings host.
def _check_host(url: str) -> None:
    host = urlparse(url).netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing to fetch host={host!r}; only {sorted(ALLOWED_HOSTS)} …")
```

**Reuse verbatim (do NOT rebuild):**
- Typed coercion helpers `coerce_price` / `coerce_date` / `normalize_status`
  (`sources.py:93-141`) — every scraped field routes through these (T-04-07-VALID).
- Status aliases `_STATUS_ALIASES` (`sources.py:63-75`) — extend for any new
  SEBI/NSE status wording, mapping into `STATUS_VALUES`.
- Lazy cached session `_session()` + `_get()` (`sources.py:149-182`): `requests_cache`
  imported inside the function (**NO NETWORK AT IMPORT** — keeps the suite offline),
  `tenacity` backoff, realistic User-Agent. New fetchers use `_get()`.
- `fetch_listing_day_close` (`sources.py:242-283`) — jugaad-data → yfinance →
  `None`(→NaN). Reuse verbatim for the listing-day close + NIFTY/VIX regime pulls.

**Live fetchers stay `# pragma: no cover - live only` seams** (`sources.py:190`,
`231`, `242`) — unit tests monkeypatch them; the live crawl is a deferred
checkpoint, exactly like the 04-07 posture.

---

### `pipelines/historical/build.py` — MODIFY for the two-source merge (service/pipeline, batch)

**Analog:** the file itself (read in full). Extend `build_panel`
(`build.py:83-121`) to merge Source A ∪ Source B and dedupe by issuer+issue_date
(P3), keeping the **per-source failure isolation** already there:
```python
raw_rows: list[dict] = []
try:
    raw_rows.extend(_sources.fetch_chittorgarh_index())     # -> replace with fetch_nse_past_issues()
except Exception as exc:  # noqa: BLE001 - per-source isolation (P14)
    console.print(f"[red]chittorgarh index failed: {exc}[/red]")
try:
    raw_rows.extend(_sources.fetch_sebi_offer_documents())  # -> the P3 withdrawn overlay
except Exception as exc:  # noqa: BLE001
    console.print(f"[red]SEBI issuer-side failed: {exc}[/red]")
```
`derive_status` (`build.py:65-75`), `assemble_panel`, `write_panel` (parquet+CSV+
README, `build.py:129-174`), and `sanity_check_median` (the >20%-median
survivorship alarm) are reused as-is. The `build` (live) vs `build-sample`
(offline CI) CLI split (`build.py:347-366`) is the template for any new offline
fixture the forecast slice needs.

---

### `data/forecasts/<drhp_id>.json` — NEW committed cache kind (data/cache, file-I/O)

**Analog:** `data/gmp/<drhp_id>.json` (shape shown in `agent/gmp_schema.py:31-45`).
Sits alongside `data/snapshots/` / `data/redflag/` / `data/gmp/` / `data/peers/`
(all present under `data/`). Commit the records (free-tier, cache-is-the-bus). Seed
hand-built offline fixtures for the render tests exactly as GMP did
(`gmp.py:23-27` mentions the two hand-seeded fixtures) — one full-render record,
one `abstain:true` record, one absent(missing-file) case.

---

### `ui/forecast_block.py` — cache-only forecast render (component, request-response)

**Analog:** `ui/snapshot_blocks.py:797-903` (`_render_gmp_spread` + `render_gmp_block`)
and `render_split_bar` (`156-204`). These are the exact grammar the UI-SPEC forecast
plot needs: **one self-contained `st.markdown(..., unsafe_allow_html=True)` with
inline `left:%` positioning, `role="img"` + a text aria-label, wrapped in
`st.container(border=True, key=…)` — never a split div** (Phase 3 white-bar lesson).

**Inline-`left:%` positioned marks in ONE markdown** (`snapshot_blocks.py:814-828`):
```python
span = spread.high - spread.low
ticks = []
for quote in record.quotes:
    pct = 50.0 if span <= 0 else (quote.value - spread.low) / span * 100.0
    pct = max(0.0, min(100.0, pct))                                 # clamp 0..100 (UI-SPEC D-1 step 5)
    ticks.append(f'<span class="drhp-gmp-tick" style="left:{pct:g}%;"></span>')
st.markdown(
    f'<div class="drhp-gmp-range-headline">{_html.escape(headline)}</div>'
    f'<div class="drhp-gmp-range" role="img" aria-label="{_html.escape(aria, quote=True)}">'
    f'{"".join(ticks)}</div>' ...,
    unsafe_allow_html=True,
)
```
→ the forecast plot computes `pos(v) = clamp((v-domain_lo)/(domain_hi-domain_lo)*100,0,100)`
(UI-SPEC D-1) and interpolates band/median/zero/GMP-marker into ONE `st.markdown`
string. Every record-sourced string `_html.escape`'d; formatted floats are safe.

**Card + heading + caption + states + footer** (`render_gmp_block`, `snapshot_blocks.py:844-903`):
```python
with st.container(border=True, key="drhpcard-gmp"):     # -> key="drhpcard-forecast"
    st.markdown('<h2 class="drhp-snapshot-block-heading">…</h2>', unsafe_allow_html=True)
    if record.is_absent:
        st.markdown(f'<div class="drhp-not-disclosed">{_html.escape(GMP_ABSENT)}</div>', ...)
    elif record.is_single_source: ...
    else: _render_gmp_spread(record)
    st.markdown(render_per_answer_footer(), unsafe_allow_html=True)   # inherited disclaimer
```
→ map `abstain` / not-covered / covered-no-GMP / full-render onto the same
`if/elif/else` state fan-out; reuse `render_per_answer_footer()` for the
`Informational only — not advice.` line, `.drhp-not-disclosed` for empty states,
and `.drhp-refusal` for the cache-error banner.

**ISOLATION (hard invariant):** this module imports ONLY `streamlit`, `ui.copy`,
`ui.format_inr`, `data.catalogue_loader`, and the two cache loaders
(`pipelines.forecast.load_forecast`, `pipelines.gmp.load_gmp`). It imports NO
`xgboost`/`mapie`/`sklearn`/`pipelines.forecast.model|walkforward|features`/`shap`.
Pinned by `test_forecast_isolation.py` (see below).

---

### GMP-implied-return conversion helper (display layer, transform)

**Analog:** `ui/format_inr.py` (read in full) + the GMP block's read-only posture.
UI-SPEC §"GMP-implied-return conversion" locks: `gmp_implied_return_pct =
gmp_premium_₹ / issue_price_₹ × 100`, computed in the DISPLAY layer from cached
`data/gmp/<drhp_id>.json` + cached issue price — **never a model feature.** Route
any ₹ input through `format_inr` (`format_inr.py:52-73`, the ONE shared rupee
formatter; `None → "—"`). If issue price is unavailable, omit the marker + gap
line (band still renders) — the honest-absence posture from `render_split_bar`'s
`if ofs_fresh is None: _render_not_disclosed()` (`snapshot_blocks.py:170-172`).

---

### `pages/02_snapshot.py` — MODIFY: insert the forecast block (route/page, request-response)

**Analog:** the file itself (read in full). **Exact insertion point:** between
`_render_peer_block(peer_record, peer_state)` (line 298) and the ranked-risks
branch (lines 304-313), INSIDE the `if record is not None:` body (UI-SPEC L5-4).
The GMP block (`_render_gmp_block`, line 335) stays last — do NOT move it.

**Cache read — copy the peer/GMP guarded try/except verbatim** (`02_snapshot.py:243-271`):
```python
peer_record = None
peer_state = "ok"
try:
    peer_record = load_peers(drhp_id)          # -> load_forecast(drhp_id)
except FileNotFoundError:
    peer_record = None
    peer_state = "missing"                      # -> honest "not covered" / abstain empty-state
except Exception:
    peer_record = None
    peer_state = "error"                        # -> amber .drhp-refusal (NOT red)
```
`drhp_id` is already allow-list-validated at `main()` top (`02_snapshot.py:190`),
so the forecast read needs no re-gate — same as peer/GMP. Add the forecast import
alongside `from pipelines.gmp import load_gmp` (line 24) and render via a
`_render_forecast_block(...)` helper mirroring `_render_peer_block`
(`02_snapshot.py:131-161`)'s error/empty/present fan-out.

---

### `pages/01_methodology.py` — MODIFY: forecaster model-card section (route/page, request-response)

**Analog:** the file itself (read in full). Append a model-card section following
the existing `render_section_head(...)` + table/card grammar. There is already a
**"Forecast coverage · MAPIE conformal · ≈ 80% · Phase 5"** row in the metrics
table (`01_methodology.py:87`) — the section deepens that into calibration plot,
PIT histogram, four baselines + DM table, `available_at<=T0` leakage audit, and
limitations (FCAST-05).

**Section-head + committed-artifact grammar** (`01_methodology.py:41,75-99,102-116`):
```python
st.markdown(render_section_head("Evaluation", "Measured, not vibed"), unsafe_allow_html=True)
_ROWS = [("Faithfulness", "RAGAS …", "&ge; 0.95", "Phase 6"), ...]
_rows_html = "".join(f'<tr><td class="m-name">{a}</td>…</tr>' for a,b,c,d in _ROWS)
st.markdown('<div class="drhp-metrics-wrap"><table class="drhp-metrics">…</table></div>',
            unsafe_allow_html=True)
```
→ reuse `.drhp-metrics` for the baselines/DM table and `.drhp-hiw-card` grid
(`01_methodology.py:113-116`) for the limitations cards. Committed PNGs embed via
`st.image(...)` reading from `model_card/`. The `Full model card →` link in
`ui/forecast_block.py` targets `/methodology` (this section).

---

### `ui/copy.py` — MODIFY: new forecast copy strings (config/copy)

**Analog:** the file itself (read in full). Add every UI-SPEC §Copywriting-Contract
string as a module-level `str` constant; the **import-time scrubber loop auto-enrolls
it** (`copy.py:686-691`):
```python
_module = _inspect.getmodule(_inspect.currentframe())
for _name, _value in list(vars(_module).items()):
    if _name.startswith("_") or not isinstance(_value, str):
        continue
    _scrub_sample_substituted(_name, _value)     # raises AssertionError at import on a banned token
```
Format-string templates (containing `{…}`) are scrubbed on a sample-substituted
instance (`copy.py:663-683`). **Register any new placeholder** (e.g. `low`, `high`,
`width`, `median`, `gmp`, `delta`, `coverage`, `mae`, `year`, `rmse`) in
`_SAMPLE_FORMAT_VALUES` (`copy.py:634-660`) or the template scrub throws `KeyError`.
**Hard constraint:** `target` is a banned stem — use "range"/"interval"/"median"
(UI-SPEC line 268); avoid `buy`/`sell`/`subscri` stems in GMP-gap wording.

---

### `app/static/drhplens.css` — MODIFY: `.drhp-forecast-*` classes (config/styles)

**Analog:** the single CSS source itself (56 KB; contains `.drhp-gmp-range`,
`.drhp-gmp-tick`, `.drhp-split-bar*`, `.drhp-metrics`, `.drhp-not-disclosed`,
`.drhp-refusal`, the four breakpoint media queries, `st-key-drhpcard-*` card
chrome). Add the `.drhp-forecast-*` classes from UI-SPEC §"New CSS classes"
(lines 356-368) consuming the CURRENT dark `--drhp-*` tokens — the band wash
`rgba(224,162,78,0.16)` + `0.60` edges is the ONLY new hex, derived from
`--drhp-accent`. No inline `<style>` from any module (single-source rule).

---

### Tests (mirror the tested GMP analogs)

**`tests/unit/test_forecast_isolation.py`** — the reverse of `tests/unit/test_gmp_isolation.py`
(read in full). Copy the `inspect.getsource` substring-audit exactly:
```python
FORBIDDEN_TOKENS = ("xgboost", "mapie", "sklearn", "forecast",
                    "pipelines.features", "pipelines.historical", "GRAPH.invoke")   # gmp test:25-33
for mod in _gmp_modules():
    src = inspect.getsource(mod)
    for token in FORBIDDEN_TOKENS:
        assert token not in src, f"{mod.__name__} must not reference {token!r} …"    # gmp test:57-64
```
**Two directions** (RESEARCH §Isolation, lines 486-491): (1) render-side —
`ui.forecast_block` + its `pages/02_snapshot.py` call site reference none of
`{xgboost,mapie,sklearn,conformal,pipelines.forecast,pipelines.features,pipelines.historical,shap}`;
(2) predictor-side — `pipelines.forecast.*`/`pipelines.features.*` source contains
no `gmp` reference (the existing `test_gmp_isolation.py:13` docstring already
reserves this reverse audit for Phase 5).

**`tests/unit/test_forecast_schema.py`** — mirror `tests/unit/test_gmp_schema.py`
(read in full): `from_json(to_json())` round-trip, abstain/covered/missing as
first-class states (analog of absent/single-source/multi at `test_gmp_schema.py:68-104`),
and the flat `to_dict` shape assertion (`test_gmp_schema.py:125-136`).

**`test_forecast_block_render.py` / `..._metrics` / `..._cqr_interval` /
`..._baselines_dm` / `..._walkforward_no_lookahead` / `..._features_available_at`**
— posture analog `tests/unit/test_gmp_precompute.py` (read lines 1-70): fully
offline, monkeypatch the model/fetcher seams (`monkeypatch.setattr(...)`, no live
network/training under `pytest tests/unit`). `test_walkforward_no_lookahead`
asserts `train.listing_date.max() < ipo.issue_date` per fold (RESEARCH §Validation
line 584) — no repo analog for the assertion body, but the fixture-panel +
monkeypatch scaffold copies GMP precompute's.

**`tests/unit/test_historical_panel.py`** (EXTEND, exists) — add an assertion that
the two-source merge yields non-zero `withdrawn`/`delisted` rows (P3), with
fetchers monkeypatched. Plus a new `@pytest.mark.integration` nightly test hitting
live NSE `public-past-issues` (CLAUDE.md India-data requirement; marker exists per
RESEARCH §Test Framework line 578).

---

## Shared Patterns

### Allow-list path gate (V5 / path-traversal — applies to every `data/forecasts/` access)
**Source:** `data/catalogue_loader.py:75-88` (`is_known_drhp_id`) + `pipelines/gmp.py:79-92` (`_gmp_path`).
**Apply to:** `pipelines/forecast.load_forecast`, `pipelines/forecast/precompute.py`, and (already satisfied) the `pages/02_snapshot.py` render.
Gate the id BEFORE forming any path or doing any work — never interpolate an
unvalidated `drhp_id` into a filesystem path.

### Cache-first render, guarded try/except (never an unhandled exception)
**Source:** `pages/02_snapshot.py:243-271` (peer + GMP reads).
**Apply to:** the forecast block read. `FileNotFoundError` → honest empty-state
(not-covered/abstain); any other `Exception` → amber `.drhp-refusal` (NOT red);
the rest of the page renders regardless.

### Per-IPO failure isolation in batch CLIs (P14)
**Source:** `pipelines/gmp.py:203-223`, `pipelines/snapshot.py:292-318`, `pipelines/redflag.py:330-361`.
**Apply to:** `pipelines/forecast/precompute.py` `precompute-all`. One IPO's
exception is logged (`# noqa: BLE001`) and skipped; it never aborts the batch.

### Record codec: `to_dict` / `to_json(indent=2)` / `from_dict` / `from_json`
**Source:** `agent/gmp_schema.py:137-159`.
**Apply to:** `agent/forecast_schema.py`. `indent=2, ensure_ascii=False` keeps the
committed cache diff-reviewable.

### Typed coercion + replace-with-NaN (never drop, never fabricate)
**Source:** `pipelines/historical/sources.py:93-141` (`coerce_price`/`coerce_date`/`normalize_status`) + `pipelines/historical/__init__.py:81-172` (`_to_float_or_nan`, `assemble_panel`).
**Apply to:** the Source A/B fetchers and `pipelines/features/build.py`. A missing
value is NaN-retained and COUNTED, never a fabricated 0.

### Import-boundary isolation via `inspect.getsource` substring audit
**Source:** `tests/unit/test_gmp_isolation.py` (whole file); same grammar in `ui/methodology_pane.py:19-22` (no-live-client note).
**Apply to:** `test_forecast_isolation.py` (both directions) — the load-bearing
GMP/model isolation invariant (D4-03 / GMP-02 / FCAST-02).

### Import-time copy scrubber assertion (TRUST-03)
**Source:** `ui/copy.py:619-691`.
**Apply to:** every new forecast string. A banned token (esp. the `target` stem)
raises `AssertionError` at import — before any request is served.

### SSRF host allow-list (extend, never derive a URL from input)
**Source:** `pipelines/historical/sources.py:38-85`.
**Apply to:** the Source A/B fetchers — add `www.nseindia.com` (+ confirm SEBI
host) to `ALLOWED_HOSTS`; `_check_host` refuses anything else.

### NO NETWORK / NO MODEL AT IMPORT (keeps the whole suite offline)
**Source:** `pipelines/historical/sources.py:22-25,149-159` (lazy client imports); `snapshot.py:118` / `redflag.py:164` (`from agent.graph import GRAPH` deferred inside the function).
**Apply to:** `pipelines/forecast/*` — import `xgboost`/`mapie`/`shap` lazily
inside the functions that train, so importing the package (and running unit tests)
never pulls the modeling stack. The record schema + loader stay import-light.

---

## No Analog Found

The modeling core is genuinely new — the codebase has zero XGBoost/MAPIE/sklearn/
SHAP/matplotlib code today. These files copy from `05-RESEARCH.md`, not a repo file:

| File | Role | Data Flow | RESEARCH reference |
|------|------|-----------|--------------------|
| `pipelines/forecast/model.py` | model wrapper | transform | §Pattern 1 (lines 254-283): 3× `XGBRegressor(reg:quantileerror)` in order `[lower, upper, median]` → `ConformalizedQuantileRegressor(prefit=True)` → `conformalize` → `predict_interval` |
| `pipelines/forecast/walkforward.py` | model loop | batch | §Pattern 2 (lines 285-307): expanding-window as-of-T0; `pool = rows[listing_date < issue_date]`; train/calib split; one OOS band per IPO |
| `pipelines/forecast/baselines.py` | model + stats | transform | §Code Examples (lines 417-446): 4 baselines scored as-of-T0 + inline `dm_test` (avoid the `dieboldmariano` dep) |
| `pipelines/forecast/diagnostics.py` | metrics + plots | transform → PNG | §Code Examples (lines 402-415): `global_metrics` (coverage/MAE/per-year RMSE); calibration/PIT/SHAP via matplotlib (partial posture-analog: `validate.py` flag-text shape) |
| `model_card/MODEL_CARD.md` + PNGs | committed artifact | file-I/O | FCAST-05; nearest writer analog is `build.py:177-251` `_write_readme` (assemble a committed markdown from computed stats) |
| R²>0.5 leakage alarm (inside `pipelines/features` or `diagnostics`) | guard | transform | §Pattern 3 line 319; posture-analog `validate.sanity_check_median` `(value, flag_or_None)` |

**Planner guidance:** for the six no-analog files, cite the RESEARCH line ranges
above directly in the plan action; do NOT invent a repo analog. Every SURROUNDING
concern (record I/O, allow-list gate, CLI isolation, offline test scaffold,
lazy-import discipline) DOES have a tight analog cited in §Pattern Assignments —
so the new code sits inside a fully-patterned shell.

---

## Metadata

**Analog search scope:** `pipelines/` (snapshot, redflag, gmp, historical/*),
`data/` (catalogue_loader, cache-kind layout), `ui/` (snapshot_blocks, copy,
format_inr, methodology_pane), `pages/` (01_methodology, 02_snapshot),
`tests/unit/` (gmp_isolation, gmp_schema, gmp_precompute, historical_panel),
`agent/gmp_schema.py`, `app/static/drhplens.css`.
**Files read in full for excerpts:** `pipelines/snapshot.py`, `pipelines/redflag.py`,
`pipelines/gmp.py`, `data/catalogue_loader.py`, `tests/unit/test_gmp_isolation.py`,
`pipelines/historical/__init__.py`, `pipelines/historical/sources.py`,
`pipelines/historical/build.py`, `pipelines/historical/validate.py`,
`pages/02_snapshot.py`, `pages/01_methodology.py`, `ui/methodology_pane.py`,
`ui/format_inr.py`, `agent/gmp_schema.py`, `tests/unit/test_gmp_schema.py`,
`tests/unit/test_gmp_precompute.py` (partial), `ui/snapshot_blocks.py` (targeted:
render_split_bar + GMP block), `ui/copy.py` (head + scrubber loop).
**Pattern extraction date:** 2026-07-15
