# Phase 3: Structured Signal Extraction (Red-Flag Table) — Pattern Map

**Mapped:** 2026-06-25
**Files analyzed:** 19 new/modified
**Analogs found:** 17 / 19 (2 genuinely-new: `risk_idf.py`, `confidence.py`)

> EXTEND-DON'T-REBUILD phase. Almost every new file copies the shape of an
> existing, unit-tested Phase 1/2 artifact verbatim. The only from-scratch
> algorithm is the ~40-line in-corpus IDF (`pipelines/risk_idf.py`). The
> highest-value extension is the unit/tolerance reconciliation inside
> `cite_check.py` (Pattern 6 / D3-10). Concrete line-numbered excerpts below.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `agent/redflag_schema.py` | model (schema) | transform/cache | `agent/snapshot_schema.py` | **exact** (mirror union-discriminator + to_json/from_dict) |
| `pipelines/redflag.py` | pipeline | batch / offline-precompute | `pipelines/snapshot.py` | **exact** (canned-query × GRAPH.invoke loop + typer CLI) |
| `pipelines/redflag_queries.py` | config | n/a (canned-query constants) | `pipelines/snapshot_queries.py` | **exact** (dict[field_key -> query]) |
| `pipelines/confidence.py` | utility | transform (deterministic) | `agent/nodes/cite_check.py` (`_normalize`, `_extract_numbers`) + `pipelines/snapshot.py::compute_ofs_fresh` | **role-match** (no exact analog; reuses cite-check primitives) |
| `pipelines/risk_idf.py` | utility | transform (corpus stat) | `pipelines/snapshot.py::compute_ofs_fresh` (stdlib-`re` derived-field) | **partial** (NEW algorithm; mirror derived-field + policies constant posture) |
| `agent/nodes/cite_check.py` (MODIFY) | middleware (agent node) | request-response / validation | itself — extend `_extract_numbers` / `_numbers_subset` | **exact** (in-place extension) |
| `scripts/eval_extraction.py` | test (eval harness) | batch | `scripts/run_eval.py` | **role-match** (load jsonl → score → dated md report) |
| `scripts/run_eval.py` (MODIFY) | test (eval harness) | batch | itself — add numeric-faithfulness track | **exact** (in-place extension) |
| `scripts/release_gate.py` | config (deploy tooling) | batch / gate | `scripts/run_eval.py::_check_env` + `scripts/calibrate_gate1.py` | **role-match** (env fail-fast + sys.exit + md report) |
| `Makefile` (NEW) | config | n/a | none in repo (verified MISSING) | **no analog** |
| `eval/gold/extraction_labels.jsonl` | test fixture | n/a | `tests/eval/gold_set.jsonl` | **exact** (jsonl-per-line label rows) |
| `eval/gold/numeric_eval.jsonl` | test fixture | n/a | `tests/eval/gold_set.jsonl` (numeric category rows) | **exact** |
| `eval/gold/boilerplate_phrases.txt` | config | n/a | none (new hand-curated floor list) | **no analog** |
| `eval/gold/extraction_rubric.md` | docs | n/a | none (new labeling protocol) | **no analog (doc)** |
| `ui/snapshot_blocks.py` (MODIFY) | component | request-response (render) | itself — `render_split_bar`, `render_risk_block`, `_render_not_disclosed` | **exact** (extend in place) |
| `ui/methodology_pane.py` (NEW, optional) | component | render (read cache) | `ui/expander.py` + `ui/snapshot_blocks.py::_render_expanders` | **role-match** |
| `ui/copy.py` (MODIFY) | config | n/a | itself — add scrubber-guarded Phase 3 strings | **exact** (import-time scrubber assertion) |
| `app/static/drhplens.css` (MODIFY) | config (styles) | n/a | itself — add `.drhp-redflag-*` / `.drhp-spec-meter` classes | **exact** (single CSS source of truth) |
| `pages/02_snapshot.py` (MODIFY) | route (page) | render | itself — add the 2 new blocks + panes | **exact** |

---

## Critical Verifications (answer the orchestrator's two open questions)

### Q: Does the cached structure already retain the retrieval query + full chunk list the methodology pane (D3-17) needs?

**Partially — precompute MUST persist more.** Verified against the real code:

- **Retrieval query** — NOT persisted today, but it does NOT need to be. It is a
  *known constant per field key* (`SNAPSHOT_QUERIES[field_key]`; Phase 3 adds
  `REDFLAG_QUERIES[field_key]`). For Q&A it is the user `question`. The pane can
  read it from the constants dict or the chat turn. **No cache change needed for the query line.**
- **Cited sources (score / section / span)** — ALREADY persisted. Each
  `GroundedAnswer.claims[].sources[]` is a `RetrievedChunkRef` carrying
  `score` (`schemas.py:34-37`), `section` (`:33`), `verbatim_span` (`:38-41`).
  `SnapshotRecord.to_dict()` dumps the full `GroundedAnswer.model_dump()`
  (`snapshot_schema.py:94`), so these survive into `data/snapshots/<id>.json`.
  **The "Retrieved chunks (with scores)" + "Sources cited" pane lines are already covered.**
- **Full reranked chunk list (beyond cited sources)** — NOT persisted.
  `state["reranked_top_k"]` exists only at runtime (`state.py:48`, consumed by
  `cite_check.run` `:199`) and is dropped after `GRAPH.invoke` returns in
  `snapshot.py:122`. **If the pane must show non-cited retrieved chunks, the
  redflag precompute loop must capture `state["reranked_top_k"]` into the new
  `RedFlagRecord` (the only genuinely-new field to persist).** Recommendation
  (matches RESEARCH A3): persist the minimum — the cited `sources[]` scores are
  likely sufficient for UI-SPEC; avoid persisting full chunk text to keep the cache small.
- **Prompt used** — static file `agent/prompts/generate.md`; read at render, never cached.
- **Eval scores** — read from the latest committed `eval/reports/*.md`; never recomputed (D3-17).

### Q: Confirm the only genuinely-new-from-scratch code.

Confirmed: **`pipelines/risk_idf.py`** (in-corpus IDF over n≈8 risk sections +
boilerplate floor, ~40 lines stdlib `math.log` + `collections.Counter`) is the
sole new *algorithm*. **`pipelines/confidence.py`** is new as a file but is pure
composition of existing `cite_check` primitives — not a new algorithm. The new
gold/config/doc files (`extraction_labels.jsonl`, `numeric_eval.jsonl`,
`boilerplate_phrases.txt`, `extraction_rubric.md`, `Makefile`) are data/tooling
with no code analog.

---

## Pattern Assignments

### `agent/redflag_schema.py` (model, mirror of `agent/snapshot_schema.py`)

**Analog:** `agent/snapshot_schema.py` (120 lines — copy the whole shape).

**Union-discriminator serialization** (`snapshot_schema.py:39-54`) — copy verbatim:
```python
def _dump_field(value: GroundedAnswer | RefusalResponse) -> dict:
    if isinstance(value, RefusalResponse):
        return {"refusal": value.model_dump()}
    return value.model_dump()

def _load_field(raw: dict) -> GroundedAnswer | RefusalResponse:
    if "refusal" in raw:                       # discriminator: presence of "refusal"
        return RefusalResponse.model_validate(raw["refusal"])
    return GroundedAnswer.model_validate(raw)   # else it's a GroundedAnswer dump
```

**Record shape + to_json/from_dict** (`snapshot_schema.py:57-120`) — mirror,
adding `confidence_tier`/`confidence_score` per field and a `ranked_risks` list:
```python
class RedFlagField(BaseModel):
    value: GroundedAnswer | RefusalResponse        # reuse locked schemas verbatim
    confidence_tier: Literal["high","medium","low"] | None = None  # None when not-disclosed (D3-03)
    confidence_score: float | None = None          # 0.00-1.00, surfaced only in pane (D3-02)

class RedFlagRecord(BaseModel):
    drhp_id: str
    computed_at: str
    fields: dict[str, RedFlagField] = Field(default_factory=dict)   # 7 canonical keys
    ranked_risks: list[RankedRisk] = Field(default_factory=list)    # ordered by descending idf (D3-15)
    model_config = {"arbitrary_types_allowed": True}
    # to_dict / to_json (indent=2) / from_dict / from_json — copy snapshot_schema.py:89-120
```
**Field-key validator** (`snapshot_schema.py:75-87`): reuse the `frozenset`
allow-list guard; lock to the 7 canonical keys (UI-SPEC fixed order).
Store at `data/redflag/<drhp_id>.json` (new dir mirroring `data/snapshots/`).

**Do NOT** rename `GroundedAnswer`/`Claim`/`RefusalResponse` fields — they are
locked (`schemas.py:1-11`; METHOD-01 + chip renderer depend on `claim_id` regex `^c_[a-z0-9]{6,16}$`).

---

### `pipelines/redflag.py` (pipeline, exact mirror of `pipelines/snapshot.py`)

**Analog:** `pipelines/snapshot.py` (322 lines).

**Imports + dir + typer setup** (`snapshot.py:16-32`):
```python
import json
from datetime import datetime, timezone
from pathlib import Path
import typer
from rich.console import Console
from agent.redflag_schema import RedFlagRecord
from compliance.scrubber import scrub
from pipelines.redflag_queries import REDFLAG_QUERIES

app = typer.Typer(help="DRHPLens red-flag pre-compute pipeline.")
REDFLAG_DIR = Path(__file__).parent.parent / "data" / "redflag"
```

**The canned-query × GRAPH.invoke loop** (`snapshot.py:118-150`) — copy the
control flow verbatim; add the confidence classifier on the grounded branch:
```python
from agent.graph import GRAPH                          # lazy import inside precompute
for field_key, query in REDFLAG_QUERIES.items():
    state = GRAPH.invoke({"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0})
    grounded_answer = state.get("grounded_answer")
    refusal = state.get("refusal")
    if grounded_answer is not None and _scrub_passes(grounded_answer):   # :128-130
        tier, score = classify_confidence(grounded_answer)               # NEW (D3-01)
        fields[field_key] = RedFlagField(value=grounded_answer,
                                         confidence_tier=tier, confidence_score=score)
    elif refusal is not None:                                            # :142-143
        fields[field_key] = RedFlagField(value=refusal)                  # no confidence on absence (D3-03)
    else:
        fields[field_key] = RedFlagField(value=_make_refusal_response(   # :147 defensive fallback
            "unsupported_claim", "Not disclosed in DRHP"))
    # OPTIONAL (D3-17): capture state["reranked_top_k"] here if the pane needs non-cited chunks
```

**Reuse, don't re-extract, field #2 (OFS vs fresh):** `compute_ofs_fresh` already
exists (`snapshot.py:174-273`) and is invoked at `snapshot.py:152`. Call it on the
snapshot's `use_of_proceeds` field rather than re-deriving — RESEARCH Pattern 1 table row 2.

**Helpers to copy verbatim:** `load_snapshot`/`_snapshot_path` (`:47-67`),
`_make_refusal_response` (`:70-78`), `_scrub_passes` (`:81-84`).

**CLI** (`snapshot.py:281-318`): copy `precompute-one` + `precompute-all` (the
per-IPO failure-isolation try/except `:308-313` is the locked batch posture).

---

### `pipelines/redflag_queries.py` (config, exact mirror of `pipelines/snapshot_queries.py`)

**Analog:** `pipelines/snapshot_queries.py` (46 lines). Copy the module-docstring
"treat edits as reviewable" framing and the `dict[str, str]` shape. Define the 7
canonical keys in UI-SPEC fixed order: `rpt_pct`, `ofs_vs_fresh`, `promoter_pledge_pct`,
`customer_concentration`, `auditor_history`, `debt_trajectory`, `going_concern`.
Keep keys in sync with `RedFlagRecord` field-key validator (the snapshot module
notes this sync requirement at `snapshot_schema.py:33`).

---

### `agent/nodes/cite_check.py` (MODIFY — D3-10, highest-value extension)

**Analog:** itself (237 lines). The numeric antibody already exists; extend it.

**Existing exact-string numeric check** (`cite_check.py:53-71`) — the code to extend:
```python
def _extract_numbers(s: str) -> set[str]:
    s_no_commas = re.sub(r"(\d),(\d)", r"\1\2", s)   # strips Indian thousands commas already
    return set(re.findall(r"\d+(?:\.\d+)?", s_no_commas))

def _numbers_subset(claim_numbers: set[str], window_numbers: set[str]) -> bool:
    if not claim_numbers:
        return True
    return claim_numbers.issubset(window_numbers)     # <-- EXACT-STRING; the false-fail risk
```

**Extension required (Pitfall 1 / RESEARCH Pattern 6):** add lakh (×1e5) / crore
(×1e7) / million (×1e6) unit reconciliation + a relative tolerance match
(`abs(claim - window)/window <= tol`) so "₹11,247 crore" grounds against
"1,12,470 lakh". Today exact-subset would FALSE-FAIL legitimate normalizations
and sink the 0.95 gate. Add `tol` as a constant in `agent/policies.py` (see
shared pattern below). Reuse the existing `_normalize` (`:34-45`) — do NOT write
a second normalizer.

**The grounding loop that consumes it** (`cite_check.py:146-155`) is unchanged in
structure; only `_numbers_subset` gets the tolerance/unit logic. The
SKELETON §D invariant holds: **NO LLM client import in this file** (`:10-13`) —
the extension stays deterministic.

---

### `pipelines/confidence.py` (utility — D3-01, new file, no algorithm)

**Analogs:** `agent/nodes/cite_check.py::_normalize`/`_extract_numbers`
(`:34-61`) for the verbatim-match primitive; `pipelines/snapshot.py::compute_ofs_fresh`
(`:174-273`) for the "deterministic post-extraction derive over claims" posture.

**Rubric** (`classify_confidence(ga) -> (tier, score)`, no LLM):
- **high** = emitted value appears verbatim in cited `claim.verbatim_span` after
  `cite_check._normalize` (exact substring).
- **medium** = value is a numeric *transformation* of source numbers (use
  `_extract_numbers` to compare) — e.g. RPT% = amount/revenue — reconcilable within tolerance.
- **low** = support spans multiple `sources[]` with different `.section` values
  (`schemas.py:33` `section`; `:108` `sources` list).

Map tier→score (high≈0.9 / med≈0.7 / low≈0.5) OR derive from the `token_set_ratio`
already computed by `cite_check`. Score shown only in the pane (D3-02).
**Reuse cite_check primitives — do not re-implement normalization** (RESEARCH §Don't Hand-Roll).

---

### `pipelines/risk_idf.py` (utility — D3-14, THE only new algorithm)

**Partial analog:** `pipelines/snapshot.py::compute_ofs_fresh` (`:174-273`) — same
"stdlib-`re` over claims, return a neutral derived structure, no verdict field" posture.

**Algorithm (stdlib `math.log` + `collections.Counter`, ~40 lines):**
1. Normalize each risk statement via `cite_check._normalize` (one shared normalizer).
2. Phrase-level shingles (3-5 word n-grams — boilerplate is phrase-level, Pitfall 2).
3. `df(term)` = #risk-sections containing term; `idf = log(N/(1+df))`, N=corpus size (n≈8 from `load_catalogue()`).
4. Risk score = mean/max IDF of salient terms; higher = more issuer-specific.
5. Boilerplate floor: if normalized risk `rapidfuzz.token_set_ratio >= ~85` against
   any phrase in `eval/gold/boilerplate_phrases.txt`, clamp to bottom band.
6. Map score → UI bands (`Issuer-specific` / `Mostly issuer-specific` / `Industry-standard`);
   thresholds in `agent/policies.py`, documented in the rubric (D3-14).

**Corpus source:** `data/catalogue_loader.py::load_catalogue()` (`:51-66`) gives the
8 IPO rows; right-size N to actually-ingested DRHPs (D3-05; only `swiggy_2024_11`
seeded today per `data/snapshots/`). Honesty note: document n≈8 as small.

---

### `scripts/eval_extraction.py` (test/eval — D3-07, role-mirror of `scripts/run_eval.py`)

**Analog:** `scripts/run_eval.py` (315 lines).

**Reuse the harness skeleton:** `_check_env()` fail-fast (`run_eval.py:35-41`),
project-root-on-path (`:31-32`), jsonl loader (`:138-142`), and the **dated
markdown-to-`eval/reports/` writer** (`:244-305`) — the report sink the
methodology pane reads.

**Per-field-type scorer (D3-07) — new logic, not in run_eval:**
- numeric (fields 1,2,3,6): `abs(pred-gold) <= tolerance` (per-field, documented).
- boolean (field 7 going-concern): exact match.
- set/list (fields 4,5): rapidfuzz set-overlap F1 (RESEARCH §Code Examples):
```python
from rapidfuzz import fuzz
def set_overlap_f1(pred, gold, thresh=85):
    matched = sum(1 for g in gold if any(fuzz.token_set_ratio(g, p) >= thresh for p in pred))
    if not pred and not gold: return 1.0
    prec = matched/len(pred) if pred else 0.0
    rec  = matched/len(gold) if gold else 0.0
    return 0.0 if prec+rec == 0 else 2*prec*rec/(prec+rec)
```
- not-disclosed = first-class label; a refusal where gold says absent = correct (D3-03). Do NOT drop refusals.

**Split by confidence bucket (D3-04):** report F1 separately for high/med/low —
mirror the per-category summary table loop (`run_eval.py:278-292`). Each metric
gets an interpretation paragraph (P10).

---

### `scripts/run_eval.py` (MODIFY — D3-11/13 numeric track)

**Analog:** itself. Add a numeric-faithfulness track: load `eval/gold/numeric_eval.jsonl`
(~50 numeric-only Qs, same jsonl shape as `gold_set.jsonl`), run the agent, and
for each emitted number apply the **extended `cite_check` per-number grounding**.
`numeric_faithfulness = fraction of eval Qs whose every emitted number grounds`.
Reuse the existing `_normalize` (`:49-53`) and report writer. Covers all numeric
surfaces (Q&A + snapshot + red-flag) per D3-13.

---

### `scripts/release_gate.py` + `Makefile` (NEW — D3-12)

**Analogs:** `scripts/run_eval.py::_check_env` (`:35-41`) for env fail-fast;
`scripts/calibrate_gate1.py` for the sweep-and-recommend CLI posture; no Makefile
in repo (verified MISSING).

**Gate body:** run the numeric track → compute `numeric_faithfulness` → if `< 0.95`,
write `eval/reports/<date>-numeric-gate.md` AND `sys.exit(1)` (enforcement over
discipline — Pitfall 4). If `>= 0.95`, print OK. `Makefile` `release` target calls it
(Make stops on non-zero). **Offline fixture test** `tests/eval/test_release_gate.py`:
feed a synthetic 0.94 result → assert non-zero exit; 0.96 → assert pass (D3-12,
unit-tests the gate LOGIC without live infra).

---

### `ui/snapshot_blocks.py` (MODIFY — red-flag rows + IDF meter, exact self-extension)

**Analog:** itself (274 lines). Three existing renderers to copy from:

**Not-disclosed row** (`snapshot_blocks.py:31-36`, `_render_not_disclosed`) — reuse
verbatim for D3-03 rows; OMIT the confidence label (L3-3):
```python
st.markdown(f'<div class="drhp-not-disclosed">{_html.escape(FIELD_NOT_DISCLOSED_NOTE)}</div>',
            unsafe_allow_html=True)
```

**Citation expanders** (`:39-54`, `_render_expanders`) — reuse for each red-flag
value's citation chips (values are `GroundedAnswer`s rendered by the UNCHANGED
`render_answer_with_chips` `:76`).

**Split-bar grammar for the specificity meter** (`:103-151`, `render_split_bar`) —
copy the accent-fill-on-neutral-track construction + the `role="img"` aria-label
pattern for `.drhp-spec-meter` (UI-SPEC R-2: same grammar, NOT red/green):
```python
st.markdown(
    f'<div class="drhp-split-bar" role="img" aria-label="{_html.escape(aria_label, quote=True)}">'
    f'<div class="drhp-split-bar-ofs" style="width:{ofs_pct}%;"><span>{ofs_label}</span></div>...'
)
```

**Risk-block counter** (`:229-264`, `render_risk_block`) — extend its
`RISK_COUNTER_TEMPLATE` per-claim loop (`:252-261`) to append the specificity word
+ render the meter (UI-SPEC: `Risk {n} of {m} · {specificity}`). Single ranked
list, ordered by `RankedRisk.idf_score` (L3-4).

---

### `ui/methodology_pane.py` (NEW optional — METHOD-01, role-mirror)

**Analogs:** `ui/expander.py::render_citation_expanders` (`:22-87`) for the
descriptor + `metadata_footer` (`:70-72`); `ui/snapshot_blocks.py::_render_expanders`
(`:39-54`) for the `st.expander` + `.drhp-snippet` rendering.

**Pane content (all cached/committed, NO live call — Pattern 8):**
| Pane line | Source (verified) |
|-----------|-------------------|
| Retrieval query | `REDFLAG_QUERIES[field_key]` constant / Q&A `question` |
| Retrieved chunks + scores | `claim.sources[].score`/`.section`/`.verbatim_span` (`schemas.py:33-41`) |
| Prompt used | static `agent/prompts/generate.md` |
| Sources cited | `ui/expander.py` `metadata_footer` (`:70-72`), reuse verbatim |
| Eval scores + numeric confidence | parse latest committed `eval/reports/*.md` (NOT recomputed); `confidence_score` from `RedFlagField` |

Use `st.expander("Show your work", expanded=False)` (UI-SPEC R-3). No LLM/Qdrant
import in this module (Pitfall 5).

---

## Shared Patterns

### Tunable constants → `agent/policies.py` (single source of truth)
**Source:** `agent/policies.py` (96 lines) — every threshold lives here, no node
hard-codes one (`:1-14`). `CITE_CHECK_TOKEN_RATIO=80` (`:69`) and
`CITE_CHECK_SPAN_TOLERANCE_CHARS=50` (`:75`) are the existing pattern.
**Apply to:** the new numeric-reconciliation tolerance (D3-10), IDF band thresholds
(D3-14), F1 numeric tolerances (D3-07), the 0.95 gate threshold (D3-12). Add each
as a documented constant with a calibration comment (mirror the `GATE1_THRESHOLD`
calibration-comment posture `:38-44`).

### Banned-token scrubber on ALL new copy → `ui/copy.py`
**Source:** `ui/copy.py:244-305` — import-time scrubber assertion over every string
constant, with sample-substitution for format templates (`:277-297`).
**Apply to:** every new Phase 3 user-facing string (red-flag headings, confidence
labels, specificity words, "Show your work", methodology pane labels — UI-SPEC
Copywriting Contract). Add them to `ui/copy.py` so the import-time assertion guards
them (L3-8). Existing anchors to copy beside: `FIELD_NOT_DISCLOSED_NOTE` (`:222`),
`RISK_COUNTER_TEMPLATE` (`:219`), `SPLIT_BAR_*` (`:210-217`). Add the new format keys
(`specificity`, `pct`, `confidence_tier`) to `_SAMPLE_FORMAT_VALUES` (`:260-274`).

### Shared text normalization → `cite_check._normalize` / `_extract_numbers`
**Source:** `agent/nodes/cite_check.py:34-61`.
**Apply to:** confidence rubric, IDF tokenization, F1 matching, numeric gate. ONE
normalization path across cite-check + eval + IDF (RESEARCH §Don't Hand-Roll — "consistency is correctness here").

### Union-discriminator cache codec → `SnapshotRecord` `{"refusal": ...}` convention
**Source:** `agent/snapshot_schema.py:39-54, 89-120`.
**Apply to:** `RedFlagRecord` serialization. Do not write a new JSON codec.

### Offline-precompute / online-read split ("storage is the integration bus")
**Source:** `pipelines/snapshot.py` writes; `pages/02_snapshot.py` + `ui/snapshot_blocks.py` read.
**Apply to:** red-flag extraction (batch write to `data/redflag/`), confidence, IDF —
all precomputed; UI/pane is pure render (D3-17/P19). No agent call at request time.

### Dated markdown report → `eval/reports/`
**Source:** `scripts/run_eval.py:244-305` (date-stamped filename, summary table + per-entry table + interpretation notes).
**Apply to:** `eval_extraction.py`, `release_gate.py`, the numeric track. The
methodology pane reads the latest committed report from this sink (D3-17).

### Per-IPO failure isolation in batch loops
**Source:** `pipelines/snapshot.py:306-314` (try/except per IPO, log + skip, don't abort).
**Apply to:** `pipelines/redflag.py` `precompute-all`, the IDF corpus build.

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `pipelines/risk_idf.py` (algorithm core) | utility | In-corpus IDF is genuinely new — no existing TF-IDF/corpus-statistic code in the repo. Stdlib `math.log` + `collections.Counter`; mirror `compute_ofs_fresh`'s derived-field posture for the wrapper, but the IDF math is from scratch (RESEARCH Pattern 4). |
| `Makefile` | config | Verified MISSING in repo. No build-tooling analog; create fresh with a single `release` target (D3-12). |
| `eval/gold/boilerplate_phrases.txt` | config | New hand-curated floor list; no analog. |
| `eval/gold/extraction_rubric.md` | docs | New labeling protocol (D3-08); no analog. Documents numeric tolerances + IDF thresholds per discretion. |

---

## Metadata

**Analog search scope:** `agent/`, `agent/nodes/`, `pipelines/`, `scripts/`, `ui/`,
`pages/`, `compliance/`, `data/`, `tests/eval/`, `eval/`.
**Files scanned (read in full):** `agent/snapshot_schema.py`, `agent/schemas.py`,
`agent/nodes/cite_check.py`, `agent/state.py`, `agent/policies.py`,
`pipelines/snapshot.py`, `pipelines/snapshot_queries.py`, `scripts/run_eval.py`,
`ui/snapshot_blocks.py`, `ui/chip.py`, `ui/expander.py`, `ui/copy.py` (scrubber block),
`data/catalogue_loader.py`, `data/catalogue.json`, `tests/eval/gold_set.jsonl`.
**Directory inventory:** confirmed no Makefile, no CSS outside `app/static/drhplens.css`,
only `data/snapshots/swiggy_2024_11.json` seeded, `eval/reports/` empty (`.gitkeep` only).
**Pattern extraction date:** 2026-06-25
