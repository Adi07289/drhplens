# Phase 3: Structured Signal Extraction (Red-Flag Table) - Research

**Researched:** 2026-06-25
**Domain:** Structured NLP extraction over Indian DRHPs + per-field-type F1 evaluation + deterministic numeric-faithfulness release gate + in-corpus IDF risk bucketing + cached methodology pane — all built on the shipped Phase 1/2 grounded-pipeline + claim_id + SnapshotRecord contracts.
**Confidence:** HIGH (this is an extend-don't-rebuild phase; the standard stack is locked and already in the repo, and every new piece is a deterministic extension of an existing, unit-tested node or pipeline).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D3-01 .. D3-17 — research the HOW, do not re-litigate)

**Confidence Scoring (EXTRACT-02)**
- **D3-01:** Confidence derived by a deterministic **source-grounding rubric** (no extra LLM cost): **high** = value stated verbatim in the cited DRHP span; **medium** = stated but needs light parsing/aggregation; **low** = inferred across sections. Anchored to the existing `claim_id`/citation contract.
- **D3-02:** UI shows **high/med/low label up front + the numeric score revealed on expand** (in the methodology pane). No color judgment (carried-forward no-green/red invariant applies to confidence).
- **D3-03:** Field **not disclosed** → render explicit **"Not disclosed in DRHP"** by reusing the existing `RefusalResponse` path. Never a hidden row, never conflated with low-confidence.
- **D3-04:** F1 eval **reports accuracy/F1 split by confidence bucket** (high/med/low) — a confidence-reliability check countering P10.

**Gold Set + F1 (EXTRACT-03)**
- **D3-05:** Gold set **right-sized to the ingested DRHP set with honest n**; report per-field F1 with true n; document 20-30 as the committed *target* (do not fake). Coupling: F1 requires the extractor to RUN on each labeled DRHP, which requires that DRHP be ingested.
- **D3-06:** **All 7 red-flag fields are labeled.**
- **D3-07:** **Per-field-type match rules**: numeric fields match **within tolerance**; boolean fields (going-concern) match **exactly**; list/set fields (customer concentration, auditor history) score by **set overlap** (precision/recall on items).
- **D3-08:** A **written labeling protocol/rubric is committed alongside the labels** (field definitions, where to look, edge-case rules, single-labeler note).
- **D3-09:** Labels live at **`eval/gold/extraction_labels.jsonl`**; rubric committed next to it.

**Numeric-Faithfulness Gate (EVAL-03)**
- **D3-10:** A failure = a number emitted that **traces to no cited DRHP span** (per-number source-grounding). Implemented by **extending the existing non-LLM `cite_check` node to numerics** — deterministic, no LLM-judge variance.
- **D3-11:** Eval set = **hand-curated ~50 numeric-only questions** across the ingested IPOs, each with a gold numeric answer + source page.
- **D3-12:** The **≥0.95 gate enforced by a pre-deploy script / `make release`-style target** that runs the numeric eval against live services, **refuses to proceed and writes the report if <0.95**. Add a **tiny offline CI smoke test** on a fixture so the gate logic itself is unit-tested.
- **D3-13:** The gate covers **all numeric-emitting surfaces** — Q&A answers + snapshot numeric fields + red-flag table numbers.

**IDF Risk Bucketing (P12 mitigation)**
- **D3-14:** Issuer-specific vs boilerplate computed via **in-corpus IDF over the ingested DRHP risk sections (n≈8, documented as small) PLUS a hand-curated boilerplate-phrase list as a deterministic floor**.
- **D3-15:** Display = a **single ranked risk list ordered by IDF specificity**, each item showing a neutral specificity indicator; issuer-specific foregrounded by rank. No hard collapsed bucket, no red/green.

**Methodology Pane (METHOD-01)**
- **D3-16:** Pane wired on **Q&A answers + the red-flag table** (Phase 3 headline surfaces); reuse on snapshot fields if cheap.
- **D3-17:** Pane content sourced **cheaply, not via live per-expand LLM calls**: query / retrieved chunks + scores / prompt / sources shown **per claim from cached `claim_id` data**; eval scores shown from the **latest committed eval report** at answer/field level (not recomputed on expand).

### Claude's Discretion (planner resolves)
- Exact red-flag table layout — **resolved by UI-SPEC R-1**: definition-list field rows, not grid/cards.
- Whether extraction reuses the Phase 2 snapshot LLM path or a dedicated structured-extraction prompt path — **strong default: reuse the grounded pipeline so every field carries `claim_id` citations** (consistent with D2-04).
- Exact numeric tolerance per field, IDF threshold for "issuer-specific", boilerplate-phrase floor contents — **tune empirically, document the procedure** (in the labeling rubric).
- Where the ingest-for-gold-set step runs (extend `pipelines/ingest.py` loop vs a standalone eval-prep script).
- `make release` / pre-deploy script's exact name, location, report format.

### Deferred Ideas (OUT OF SCOPE)
- Expanding the gold set / IDF corpus to the full 20-30 DRHPs (bounded by `data/INGEST_ALL_LATER.md`).
- General RAGAS faithfulness ≥0.95 gate, failure gallery, full eval dashboards — Phase 6 (EVAL-01, FAILGAL-01).
- Peer multiples / GMP display — Phase 4.
- Cross-IPO red-flag comparison — v2.
- Live per-claim eval recomputation in the methodology pane — Phase 6; v1 uses cached report scores.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **EXTRACT-01** | Structured red-flag signal table per IPO (7 fields) | Reuse grounded pipeline via 7 new canned queries mirroring `SNAPSHOT_QUERIES`; cache in a `RedFlagRecord` mirroring `SnapshotRecord`. See §Architecture Pattern 1 + 2. P12 risk bucketing via §Pattern 4 (in-corpus IDF). |
| **EXTRACT-02** | Each field carries a visible extractor confidence score | Deterministic source-grounding rubric (§Pattern 3). Confidence is computed at cache-build time from the `cite_check` outcome + a light-parse classifier; stored on each field. UI per UI-SPEC L3-2. |
| **EXTRACT-03** | Extractors evaluated against a hand-labeled gold set; per-field F1 committed | Per-field-type F1 (numeric tolerance / boolean exact / set-overlap) — §Pattern 5 + §Don't Hand-Roll. Labels at `eval/gold/extraction_labels.jsonl`, rubric beside it. Right-sized n (D3-05). |
| **EVAL-03** | Numeric-faithfulness eval track + ≥0.95 release gate that refuses deploy | Extend `cite_check` numeric subset check to per-number source-grounding (§Pattern 6). `make release` gate (§Pattern 7) wrapping `scripts/run_eval.py`'s numeric track; offline CI smoke test on a fixture. |
| **METHOD-01** | "Show your work" pane revealing query / chunks+scores / prompt / sources / eval scores | All five fields already exist in cached structures (`GroundedAnswer.claims[].sources[].score`, `RetrievedChunkRef`, `SNAPSHOT_QUERIES`/red-flag queries, committed eval report) — §Pattern 8. Cached, never live (D3-17). |
</phase_requirements>

## Summary

Phase 3 is an **extend-don't-rebuild** phase. Every locked decision maps to a deterministic extension of an already-shipped, already-unit-tested Phase 1/2 artifact:

- **Red-flag extraction** = 7 new canned queries run through the *existing* `agent.graph.GRAPH` (exactly as `pipelines/snapshot.py` runs its 6), cached to a new per-`drhp_id` JSON record that mirrors `SnapshotRecord`. No new LLM path. Each field is a serialized `GroundedAnswer` (cited) or `RefusalResponse` ("Not disclosed in DRHP").
- **Confidence** = a deterministic post-hoc classifier over the *already-computed* `cite_check` result and the claim's `verbatim_span` — verbatim-match → high, light-parse/aggregation → medium, cross-section inference → low. Zero extra LLM cost (D3-01).
- **Numeric faithfulness** = the `cite_check` node *already has* a numeric-subset antibody (P2). Phase 3 promotes it to a per-number grounding gate across all numeric surfaces and exposes it as a release metric (D3-10/13).
- **F1 eval** = a small new scorer with three match modes (numeric tolerance, boolean exact, set-overlap via `rapidfuzz` which is already a dependency), run against a hand-labeled `extraction_labels.jsonl` (D3-07).
- **IDF risk bucketing** = a from-scratch but trivially small TF-IDF over n≈8 risk sections + a hand-curated boilerplate floor (D3-14). This is the only genuinely new algorithm, and it is ~40 lines.
- **`make release` gate** = a thin wrapper that runs the numeric track, exits non-zero below 0.95, and writes a report; plus an offline pytest fixture so the gate *logic* is CI-tested without live infra or API cost (D3-12).
- **Methodology pane** = pure rendering over data that *already exists* in the cached `claim_id`/`GroundedAnswer` structures + the latest committed eval report. No new computation, no live LLM call (D3-17).

**Primary recommendation:** Build a `RedFlagRecord` cache (mirror of `SnapshotRecord`) populated by a `pipelines/redflag.py` that runs the existing graph over 7 new canned queries; add a deterministic `confidence.py` rubric and a `risk_idf.py` bucketer; extend `cite_check.py` for per-number grounding and surface it through `scripts/run_eval.py` as a numeric track; gate it with a `make release` target plus an offline fixture test; render everything via the unchanged `ui/chip.py` + `ui/expander.py`. **Add zero heavy new dependencies** — `rapidfuzz` (set-overlap F1) and stdlib `math`/`collections` (IDF) cover everything. Do **not** add `scikit-learn` for F1; the per-field-type rules are not sklearn's `f1_score` shape (numeric-tolerance and set-overlap are bespoke) and a heavy CPU dep on a free HF Space is unjustified.

## Architectural Responsibility Map

DRHPLens is a Streamlit-on-HF-Spaces app with an offline-precompute/online-read split (the "storage is the integration bus" invariant). Tiers here are pipeline stages, not web tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 7-field red-flag extraction (EXTRACT-01) | Offline pipeline (`pipelines/redflag.py`) runs the agent graph | Cache store (`data/redflag/<drhp_id>.json`) | Same offline-precompute pattern as `pipelines/snapshot.py`; never run at request time (P19 demo fragility). |
| Per-field confidence scoring (EXTRACT-02) | Offline pipeline (deterministic post-extraction) | Cache store (stored on each field) | Confidence is a pure function of the already-cited claim; compute once at cache-build, read at render. |
| Numeric per-number grounding (EVAL-03) | Agent node (`agent/nodes/cite_check.py`, extended) | Eval harness (`scripts/run_eval.py` numeric track) | Grounding must run *inside* the generate→cite_check pipeline so a hallucinated number is blocked before it reaches any cache; the eval harness measures the same logic offline. |
| F1 gold-set scoring (EXTRACT-03) | Eval harness (new `scripts/eval_extraction.py` or extend `run_eval.py`) | Committed report (`eval/reports/`) + gold labels (`eval/gold/`) | Offline batch scorer; output is a committed markdown report the methodology pane reads. |
| IDF risk bucketing (P12) | Offline pipeline (`pipelines/risk_idf.py` or a step in `redflag.py`) | Cache store (specificity score per risk item) | Corpus-level statistic computed once over the ingested risk sections; the rank/score is cached on the risk list. |
| Release gate (EVAL-03) | Build/deploy tooling (`Makefile` / `scripts/release_gate.py`) | Offline CI fixture test (`tests/`) | Gate logic = deploy tooling; its *correctness* is unit-tested offline so it never silently passes. |
| Methodology pane rendering (METHOD-01) | UI (`ui/` + `pages/`) | Cache + committed report (read-only) | Pure presentation over cached `claim_id` data + latest committed eval report; no computation, no live LLM. |

**Why this matters:** The single most common misassignment here would be putting numeric grounding or confidence scoring in the UI/render tier (so it runs per-expand). The locked decisions (D3-17 "cached not live", D3-10 "inside cite_check") forbid that. Everything user-facing in Phase 3 is a *read* of precomputed/committed data.

## Standard Stack

This phase adds **no new core library**. The locked stack (CLAUDE.md / STACK.md) already contains everything needed. The table below lists only the libraries Phase 3 *touches*, with the verified-present version constraint from `requirements.txt`/`pyproject.toml`.

### Core (already in repo — reuse)
| Library | Version (declared) | Purpose in Phase 3 | Why Standard |
|---------|--------|---------|--------------|
| `rapidfuzz` | unpinned (present) `[VERIFIED: requirements.txt]` | Set-overlap F1 for list fields (customer concentration, auditor history); already powers `cite_check` token_set_ratio | Already the project's fuzzy-match tool; `token_set_ratio` + `process.extractOne` cover item-level set matching with normalization. |
| `pydantic` | `>=2.7,<3` `[VERIFIED: pyproject.toml]` | `RedFlagRecord` / `RedFlagField` schemas mirroring `SnapshotRecord` | Locked schema layer; reuse `GroundedAnswer`/`RefusalResponse` verbatim. |
| `instructor` | `>=1.15,<2` `[VERIFIED: pyproject.toml]` | Already used by the generate node; no Phase 3 change needed unless a dedicated extraction prompt is chosen (discretion — default is reuse). | Locked structured-output layer. |
| `streamlit` | `>=1.36` `[VERIFIED: pyproject.toml]` | `st.expander` for the methodology pane + red-flag rows | `st.expander` is the inherited Phase 1/2 reveal primitive (UI-SPEC R-3). |
| `typer` + `rich` | present `[VERIFIED: pyproject.toml]` | CLI for `pipelines/redflag.py` (mirror `pipelines/snapshot.py`'s `typer.Typer`) | Established pipeline-CLI pattern. |

### Supporting (stdlib — no install)
| Module | Purpose | When to Use |
|--------|---------|-------------|
| `math` (`log`), `collections.Counter` | In-corpus IDF over n≈8 risk sections (D3-14) | Trivial TF-IDF; do not pull in scikit-learn for an 8-document corpus. |
| `re`, `unicodedata` | Indian-numeral normalization (lakh/crore/₹/%) and risk-statement normalization | Already the normalization approach in `cite_check._normalize` and `snapshot.compute_ofs_fresh` — mirror it. |
| `json`, `pathlib`, `datetime` | `RedFlagRecord` (de)serialization mirroring `SnapshotRecord.to_json`/`from_dict` | Established cache-IO pattern. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib IDF over 8 docs | `scikit-learn` `TfidfVectorizer` `[VERIFIED: PyPI 1.9.0, 2026-06-02]` | sklearn is a ~30MB+ CPU dependency (now also pulls `narwhals`); overkill for an 8-document corpus on a free 2vCPU HF Space. Only justify if Phase 4/5 already pull sklearn for modeling — they do (XGBoost/MAPIE era is Phase 5), so deferring sklearn to Phase 5 keeps Phase 3's deploy lean. `[ASSUMED]` that 8-doc stdlib TF-IDF is sufficient — verify empirically per D3-14. |
| `rapidfuzz` set-overlap | `sklearn.metrics.f1_score` | sklearn's `f1_score` expects label vectors, not the per-field-type (numeric-tolerance / set-overlap) match rules D3-07 requires. The bespoke scorer is simpler and exactly matches the locked spec. |
| reuse grounded pipeline (default) | dedicated Instructor extraction prompt path | A dedicated `response_model` (e.g. `RedFlagExtraction`) would give typed fields but would NOT carry `claim_id` citations, breaking D2-04/D3-17 (methodology pane needs the claim trace). **Reuse the grounded pipeline.** |

**Installation:** No new runtime dependency required for the recommended path. If the planner chooses sklearn for IDF (not recommended), pin `scikit-learn>=1.9,<2` and add it to `requirements.txt` + `pyproject.toml` — but prefer deferring sklearn to Phase 5 where it is load-bearing.

**Version verification:** `scikit-learn` latest = **1.9.0** (released 2026-06-02, supports Python 3.11–3.14) `[VERIFIED: PyPI via WebSearch]`. `rapidfuzz` already vendored and exercised by the passing cite-check tests `[VERIFIED: requirements.txt + green test suite]`. Note: the PyPI package `sklearn` (no `scikit-`) is a deprecated/shim package and must NOT be used — always `scikit-learn` `[CITED: pypi.org/project/sklearn]`.

## Package Legitimacy Audit

> Phase 3's recommended path installs **no new package**. The audit below covers the one *optional* package (sklearn, only if the planner overrides the stdlib-IDF recommendation) and re-confirms the already-vendored libraries the phase leans on.

slopcheck was **not installable** in this research session (`pip install slopcheck` unavailable; `command -v slopcheck` → not found). Per the graceful-degradation rule, the one optional new package is tagged `[ASSUMED]` and the planner must gate its install behind a `checkpoint:human-verify` task **if** it is adopted.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `scikit-learn` (optional, NOT recommended) | PyPI | 18+ yrs | ~80M/mo | github.com/scikit-learn/scikit-learn | unavailable → `[ASSUMED]` | Defer to Phase 5; if used in P3, gate behind checkpoint:human-verify |
| `rapidfuzz` (already vendored) | PyPI | present in repo, tests green | high | github.com/rapidfuzz/RapidFuzz | n/a (already installed) | Approved (no new install) |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none. Note: the bare `sklearn` PyPI name is a known deprecated shim — never install it; use `scikit-learn`.

*slopcheck was unavailable at research time; the single optional package above is `[ASSUMED]` and the planner must gate any new install behind a `checkpoint:human-verify` task. The recommended Phase 3 path installs nothing new, so in the recommended path this section is informational only.*

## Architecture Patterns

### System Architecture Diagram

```
OFFLINE PRE-COMPUTE (run once per drhp_id; mirrors snapshot pipeline)
─────────────────────────────────────────────────────────────────────
 data/catalogue.json (8 IPOs, allow-listed)
        │
        ▼
 pipelines/redflag.py  ──for each of 7 canned red-flag queries──▶ agent.graph.GRAPH.invoke()
        │                     (retrieve → rerank → generate → cite_check → emit)
        │                                          │
        │                              GroundedAnswer (claim_id-cited)  OR  RefusalResponse
        │                                          │
        ▼                                          ▼
 confidence.py: rubric ───────────────▶  per-field confidence (high/med/low + numeric)
   (verbatim? light-parse? inferred?)              │
        │                                          ▼
 risk_idf.py: in-corpus IDF over 8 risk sections + boilerplate floor
        │                                          │
        ▼                                          ▼
 RedFlagRecord  ──serialize (mirror SnapshotRecord.to_json)──▶  data/redflag/<drhp_id>.json
        │                                                         (fields + confidence + ranked risks)
        │
 numeric grounding: cite_check per-number sub-check already ran inside GRAPH;
   a value failing numeric grounding is stored as a "blocked" RefusalResponse (UI-SPEC L3-9)

EVAL TRACK (offline; deterministic ground truth)
────────────────────────────────────────────────
 eval/gold/extraction_labels.jsonl ──▶ scripts/eval_extraction.py ──▶ eval/reports/<date>-extraction-f1.md
   (7 fields × n DRHPs, per-field-type)     (numeric tol / bool exact / set-overlap; split by confidence bucket)

 eval/gold/numeric_eval.jsonl (~50 Q) ──▶ scripts/run_eval.py (numeric track) ──▶ numeric_faithfulness score
                                                              │
                                            make release ─────┤── score ≥ 0.95 ? deploy : exit 1 + write report
                                            (offline fixture test verifies the gate LOGIC in CI)

ONLINE READ (Streamlit; no computation, no LLM)
───────────────────────────────────────────────
 pages/02_snapshot.py ──reads──▶ data/redflag/<drhp_id>.json  +  latest eval/reports/*.md
        │
        ▼
 ui/snapshot_blocks.py (red-flag rows + IDF risk list)  +  ui/chip.py (citations)  +  ui/expander.py ("Show your work")
```

A reader can trace the primary use case: a labeled DRHP is ingested → the offline pipeline runs the agent 7× → each field becomes a cited `GroundedAnswer` with a deterministic confidence → numbers are grounded by `cite_check` or blocked → the record is cached → Streamlit reads the cache and the committed eval report and renders rows + the methodology pane, all without any request-time LLM call.

### Recommended Project Structure (new files, mirroring existing patterns)
```
agent/
├── redflag_schema.py      # RedFlagRecord + RedFlagField (mirror snapshot_schema.py)
├── nodes/cite_check.py     # EXTEND: promote numeric-subset check to per-number grounding gate (D3-10)
pipelines/
├── redflag.py              # mirror snapshot.py: 7 canned queries × GRAPH.invoke → cache + CLI
├── redflag_queries.py      # mirror snapshot_queries.py: the 7 red-flag canned queries
├── confidence.py           # deterministic source-grounding rubric (D3-01)
├── risk_idf.py             # in-corpus IDF + boilerplate floor (D3-14)
scripts/
├── eval_extraction.py      # per-field-type F1 scorer (D3-07); writes eval/reports/<date>-extraction-f1.md
├── run_eval.py             # EXTEND: add numeric-faithfulness track (D3-11/13)
├── release_gate.py         # the ≥0.95 gate body called by `make release` (D3-12)
eval/gold/
├── extraction_labels.jsonl # hand labels, 7 fields × n DRHPs (D3-09)
├── extraction_rubric.md    # labeling protocol (D3-08)
├── numeric_eval.jsonl      # ~50 numeric-only Q with gold answer + page (D3-11)
├── boilerplate_phrases.txt # hand-curated IDF floor (D3-14)
Makefile                    # NEW: `release` target wrapping release_gate.py (D3-12)
ui/snapshot_blocks.py        # EXTEND: red-flag rows + IDF risk meter + methodology pane
ui/methodology_pane.py       # NEW (optional): "Show your work" expander component (METHOD-01)
data/redflag/<drhp_id>.json  # the per-IPO red-flag cache (mirrors data/snapshots/)
tests/eval/test_release_gate.py  # offline fixture test of the gate logic (D3-12)
tests/eval/test_extraction_f1.py # per-field-type scorer unit tests
```

### Pattern 1: Red-flag extraction = canned queries through the existing graph (EXTRACT-01)
**What:** Mirror `pipelines/snapshot.py` exactly. Define 7 canned queries in `pipelines/redflag_queries.py`, loop `GRAPH.invoke({"question": q, "drhp_id": id, "regenerate_attempts": 0})`, scrub, store each result as `GroundedAnswer` or `RefusalResponse`.
**When to use:** Every red-flag field. This guarantees each field carries `claim_id` citations (D2-04/D3-17) for free.
**Example (mirror of the verified existing pattern):**
```python
# Source: pipelines/snapshot.py:118-150 (verified existing code) — mirror verbatim
from agent.graph import GRAPH
from compliance.scrubber import scrub
for field_key, query in REDFLAG_QUERIES.items():
    state = GRAPH.invoke({"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0})
    ga, refusal = state.get("grounded_answer"), state.get("refusal")
    if ga is not None and scrub(ga.answer_prose).passed:
        fields[field_key] = ga          # cited GroundedAnswer
    elif refusal is not None:
        fields[field_key] = refusal     # honest "Not disclosed" (D3-03)
    else:
        fields[field_key] = _make_refusal_response("unsupported_claim", "Not disclosed in DRHP")
```

**The 7 canonical fields (UI-SPEC fixed order)** and their field-type for F1 (D3-07):
| # | Field | F1 match type | Notes |
|---|-------|---------------|-------|
| 1 | RPT % of revenue | numeric (tolerance) | derived = RPT amount ÷ revenue; often a "light-parse/aggregation" → confidence likely *medium* |
| 2 | OFS vs fresh issue % | numeric (tolerance) | **already computed** by `snapshot.compute_ofs_fresh` — reuse it, do not re-extract |
| 3 | Promoter pledge % | numeric (tolerance) | frequently *not disclosed* → `RefusalResponse` (D3-03) |
| 4 | Customer concentration | set/list (overlap) | "top 5 customers = X% of revenue"; often not disclosed |
| 5 | Auditor history | set/list (overlap) | auditor name(s) + any change/resignation flag |
| 6 | Debt trajectory | numeric or short prose | multi-year debt direction; tolerance on the values |
| 7 | Going-concern mentions | boolean (exact) | presence/absence of a going-concern statement |

### Pattern 2: RedFlagRecord cache mirrors SnapshotRecord (EXTRACT-01/02)
**What:** A `RedFlagRecord` Pydantic model with `to_json`/`from_dict` helpers identical in shape to `SnapshotRecord`, plus a per-field confidence and the ranked risk list. Each field value is `GroundedAnswer | RefusalResponse` reusing the SAME `{"refusal": ...}` discriminator convention.
**When to use:** The cache store for all red-flag output.
**Example:**
```python
# Source: agent/snapshot_schema.py (verified) — mirror the union-discriminator + to_json/from_dict
class RedFlagField(BaseModel):
    value: GroundedAnswer | RefusalResponse   # reuse locked schemas verbatim
    confidence_tier: Literal["high","medium","low"] | None = None  # None when not-disclosed
    confidence_score: float | None = None     # 0.00–1.00, surfaced only in pane (D3-02)
class RankedRisk(BaseModel):
    claim_id: str
    idf_score: float
    specificity_band: Literal["issuer_specific","mostly_issuer_specific","industry_standard"]
class RedFlagRecord(BaseModel):
    drhp_id: str
    computed_at: str
    fields: dict[str, RedFlagField]           # 7 canonical keys
    ranked_risks: list[RankedRisk]            # ordered by descending idf_score (D3-15)
```
Store at `data/redflag/<drhp_id>.json` (new dir mirroring `data/snapshots/`).

### Pattern 3: Deterministic confidence rubric (EXTRACT-02 / D3-01)
**What:** A pure function `classify_confidence(field) -> (tier, score)` with **no LLM call**. Tiers anchor to the existing `cite_check` machinery and the claim's `verbatim_span`:
- **high** = the emitted value string appears **verbatim** in the cited `verbatim_span` (exact substring after `cite_check._normalize`). This is "stated verbatim in the cited span".
- **medium** = value is present but required **light parsing/aggregation** — e.g. a numeric was computed from two cited spans (RPT% = amount/revenue), or the value is a normalized form of a differently-formatted source ("₹1,12,470 lakh" → "11,247 cr"). Detect: claim numbers are a *transformation* of source numbers (not a verbatim substring) but still numerically reconcilable within tolerance.
- **low** = the claim's support spans **multiple sections** / multiple `sources[]` with different `section` values, i.e. an inference across sections.
**Score:** map tier→a representative numeric (e.g. high≈0.9, medium≈0.7, low≈0.5) OR derive from the `cite_check` `token_set_ratio` already computed. The numeric is shown only in the pane (D3-02).
**Why deterministic:** D3-01 explicitly wants this defensible in an interview and free of LLM-self-report bias.
**Detection primitives available (verified in `cite_check.py`):** `_normalize`, `_extract_numbers` (handles Indian commas), `span_offsets`, `sources[].section`. Reuse them — do not re-implement normalization.

### Pattern 4: In-corpus IDF risk bucketing (P12 / D3-14)
**What:** Compute IDF for each risk statement across the n≈8 ingested DRHP risk sections, then order risks by descending IDF (most issuer-specific first). Add a hand-curated boilerplate-phrase floor: any risk matching a floor phrase is forced into the bottom band regardless of IDF (deterministic guard against small-n IDF noise).
**Algorithm (stdlib, ~40 lines):**
1. Normalize each risk statement (reuse `cite_check._normalize`; additionally lowercase, strip SEBI/India stop-phrases).
2. Tokenize into n-grams (sentence-level or shingle of 3–5 words is more robust than unigrams for boilerplate detection — boilerplate is *phrase*-level).
3. `df(term) = #risk-sections containing term`; `idf(term) = log(N / (1 + df))` with N=corpus size.
4. Risk score = mean (or max) IDF of its salient terms; higher = more issuer-specific.
5. Boilerplate floor: if the normalized risk fuzzy-matches (`rapidfuzz.token_set_ratio ≥ ~85`) any phrase in `eval/gold/boilerplate_phrases.txt`, clamp to bottom band.
6. Map score to UI bands (UI-SPEC R-2): top → `Issuer-specific`, middle → `Mostly issuer-specific`, bottom → `Industry-standard`. **Thresholds tuned empirically and documented in the rubric** (D3-14 / discretion).
**Honesty note (P10/P12):** document n≈8 as small; the boilerplate floor is what makes this robust *now*, IDF sharpens as the catalogue grows. State this in the methodology copy.
**Evaluate on issuer-specific recall, not gross recall** (PITFALLS P12 prevention #3) — the F1 story for risk should weight specific risks.

### Pattern 5: Per-field-type F1 scorer (EXTRACT-03 / D3-07)
**What:** `scripts/eval_extraction.py` loads `extraction_labels.jsonl`, runs (or reads the cached output of) the extractor per labeled DRHP, and scores each field with the type-appropriate rule:
- **numeric** (fields 1,2,3,6): predicted matches gold if `abs(pred - gold) <= tolerance`. Tolerance per field, documented (e.g. ±0.5 pp for percentages, ± disclosed rounding for amounts). Report precision/recall/F1 where "disclosed-correctly vs not".
- **boolean** (field 7, going-concern): exact match. F1 over {present, absent}.
- **set/list** (fields 4,5): item-level precision/recall → F1. Match items with `rapidfuzz` (auditor name variants, customer descriptors). Set-overlap F1 = `2·|pred∩gold| / (|pred|+|gold|)` on fuzzy-matched items.
- **not-disclosed handling:** treat "Not disclosed in DRHP" (RefusalResponse) as a first-class label value; a field the gold says is absent and the extractor refuses on = correct (this is the honest-signal credit, D3-03). Do NOT silently drop refusals from F1.
**Split by confidence bucket (D3-04):** report F1 separately for high/med/low-confidence predictions — the confidence-reliability check that counters P10. Each metric gets an interpretation paragraph (P10 prevention #1).

### Pattern 6: Numeric per-number grounding gate (EVAL-03 / D3-10)
**What:** The `cite_check` node **already** runs a numeric-subset check (`_numbers_subset`: every number in a claim must appear in the cited window — verified at `cite_check.py:64-71,146-155`). Phase 3 work is to:
1. **Promote it to a hard, per-number gate** for emitted numbers across all surfaces (currently it's one factor in the per-claim grounding decision). A value whose number fails grounding → the field is stored as a *blocked* `RefusalResponse` with the UI-SPEC L3-9 copy, never an unsourced number.
2. **Extend Indian-numeral normalization** so grounding is robust: lakh/crore words, ₹ symbol, `%`, Indian digit grouping (12,34,567). `_extract_numbers` already strips commas; add lakh→×1e5 / crore→×1e7 reconciliation and a tolerance match (`abs(claim_num - window_num)/window_num <= tol`) so "₹11,247 crore" grounds against "1,12,470 million" within rounding. Document the tolerance.
3. **Surface it as a release metric** (numeric_faithfulness = fraction of numeric eval Qs whose every emitted number grounds).
**Warning (from existing code):** `_numbers_subset` does **exact-string** subset matching today. A verbatim "11,247" vs a source "11247.0" or "₹11,247 crore" vs "1,12,470 lakh" would *fail* exact subset. Phase 3 MUST add tolerance/unit-aware reconciliation or the gate will false-fail on legitimate normalizations. This is the highest-value extension in the phase.

### Pattern 7: `make release` ≥0.95 gate (EVAL-03 / D3-12)
**What:** A `Makefile` `release` target → `python scripts/release_gate.py` that (a) runs the numeric track against live services, (b) computes numeric_faithfulness, (c) **exits non-zero and writes `eval/reports/<date>-numeric-gate.md` if < 0.95**, (d) only proceeds (e.g. prints "OK to push") if ≥ 0.95. Fits the solo HF-Spaces git-push deploy model (no CI secrets/API cost in the gate itself).
**Plus an offline fixture test** (`tests/eval/test_release_gate.py`): feed the gate function a synthetic results object at 0.94 and assert it exits non-zero/raises; at 0.96 assert it passes. This unit-tests the **gate logic** without live infra (D3-12). Mirror `scripts/smoke.sh`'s "test the mechanism offline" posture.
**Pattern reference:** `scripts/run_eval.py` already does `_check_env()` fail-fast and writes a dated markdown report to `eval/reports/` — reuse that structure.

### Pattern 8: Cached methodology pane (METHOD-01 / D3-17)
**What:** Pure rendering. Every datum the pane shows already lives in cached structures:
| Pane line (UI-SPEC) | Source (already exists) |
|---------------------|--------------------------|
| Retrieval query | the canned query string (`REDFLAG_QUERIES` / `SNAPSHOT_QUERIES`) for that field; for Q&A, the user question (cache per claim) |
| Retrieved chunks + scores | `claim.sources[]` → `RetrievedChunkRef.score`, `.section`, `.verbatim_span` (verified in `schemas.py:34-45`) |
| Prompt used | the committed `agent/prompts/generate.md` (static) |
| Sources cited | `ui/expander.py` `metadata_footer` (reuse verbatim per UI-SPEC) |
| Eval scores | parse the **latest committed** `eval/reports/*.md` at answer/field level — NOT recomputed |
**Critical:** the per-claim retrieval trace (query + chunks + scores) must be **persisted into the cache at precompute time** if it isn't already. Today `GroundedAnswer.claims[].sources[]` carries score/section/span, but the *retrieval query* and *full chunk list* may need to be captured into `RedFlagRecord` during precompute so the pane has them without a live call. Verify what `state["reranked_top_k"]` retains and persist the minimum needed.

### Anti-Patterns to Avoid
- **Building a dedicated Instructor extraction schema that drops claim_id** — breaks D2-04/D3-17. Reuse the grounded pipeline.
- **Computing confidence with an LLM self-report** — D3-01 forbids; use the deterministic rubric.
- **Running the methodology pane / IDF / confidence at request time** — D3-17/P19 forbid; all precomputed/cached.
- **Pulling scikit-learn for an 8-doc IDF or for F1** — heavy dep, wrong shape; stdlib + rapidfuzz suffice.
- **Exact-string number matching without unit/tolerance reconciliation** — will false-fail the 0.95 gate on legitimate lakh/crore normalizations (see Pattern 6 warning).
- **Hiding "Not disclosed" rows or dropping refusals from F1** — D3-03/D3-07 require absence to be a first-class, scored, visible signal.
- **Color-coding confidence or specificity** — UI-SPEC L3-1/L3-2; monochrome text only.
- **A hard collapsed boilerplate bucket** — D3-15/L3-4 require a single ranked list.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy item matching for set-overlap F1 (auditor/customer variants) | Custom Levenshtein/Jaccard | `rapidfuzz` (already vendored) `token_set_ratio` / `process.extractOne` | Already the project's matcher; C-fast; handles word-order + partial. |
| Text normalization for matching/IDF | New normalizer | `cite_check._normalize` + `_extract_numbers` (verified existing) | One normalization path across cite-check, eval, IDF — consistency is correctness here. |
| Cache (de)serialization with the GroundedAnswer/Refusal union | New JSON codec | `SnapshotRecord.to_json`/`from_dict` `{"refusal": ...}` discriminator pattern | Proven, unit-tested; copy the shape. |
| Running extraction queries | New LLM client / prompt path | `agent.graph.GRAPH.invoke` (the snapshot pattern) | Carries claim_id citations for free; no new compliance surface. |
| Citation rendering + chips | New renderer | `ui/chip.py` `render_answer_with_chips()` (unchanged per UI-SPEC) | Locked UI contract; red-flag values are `GroundedAnswer`s. |
| Numeric grounding | New verifier | extend `cite_check`'s existing `_numbers_subset` | The antibody already exists; promote + add tolerance, don't rebuild. |
| Eval report writing | New report tooling | `scripts/run_eval.py`'s dated-markdown-to-`eval/reports/` structure | Established report sink the methodology pane already expects. |

**Key insight:** Phase 3 has almost no genuinely new infrastructure. The only from-scratch algorithm is the ~40-line in-corpus IDF (Pattern 4); everything else is a deterministic extension or a render of existing, tested structures. The risk in this phase is *rebuilding what exists* (a new extraction path, a new normalizer, a new cache codec) rather than extending it.

## Runtime State Inventory

> Phase 3 is primarily additive (new caches, new eval files, extended nodes), but it adds persisted state and extends a shared node. Verified against the repo.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | NEW: `data/redflag/<drhp_id>.json` per-IPO red-flag cache (8 IPOs once ingested). NEW: `eval/gold/extraction_labels.jsonl`, `eval/gold/numeric_eval.jsonl`, `eval/gold/boilerplate_phrases.txt`, `eval/gold/extraction_rubric.md`. EXISTING reused: `data/snapshots/<drhp_id>.json` (`ofs_fresh` reused for field #2). | Create new cache dir + gold files (committed). Right-size to actually-ingested DRHPs (D3-05); currently only `swiggy_2024_11` is seeded (hand-seeded placeholder per STATE.md) — the rest await live ingest (`data/INGEST_ALL_LATER.md`). |
| Live service config | None new. Qdrant + Gemini/Groq config unchanged from Phase 1/2. The red-flag extraction reuses the existing graph against the same live Qdrant. | None — but the F1 eval requires each labeled DRHP to be ingested into the live Qdrant first (the D3-05 coupling). Gold-set n is bounded by `data/INGEST_ALL_LATER.md`. |
| OS-registered state | None. No new cron/scheduler/task. The existing `scripts/cron_pinger.yml` (warm-keep) is unchanged. | None. |
| Secrets/env vars | None new. `release_gate.py` reuses the existing `GEMINI_API_KEY`/`QDRANT_URL`/`QDRANT_API_KEY` (`run_eval._check_env`). No new secret. | None — reuse `_check_env`. |
| Build artifacts | NEW: `Makefile` (`release` target) — not previously present (verified `MISSING: Makefile`). EXISTING: `__pycache__` for the extended `cite_check.py` will rebuild automatically. | Add `Makefile`; no stale-artifact migration. |

**Nothing found in category (OS-registered, new secrets):** None — verified by directory inspection (no scheduler files beyond the unchanged `cron_pinger.yml`; `run_eval._check_env` enumerates the only required env vars).

## Common Pitfalls

### Pitfall 1: Numeric gate false-fails on legitimate Indian-numeral normalization (P2-adjacent)
**What goes wrong:** The existing `_numbers_subset` is exact-string. "₹11,247 crore" in the answer vs "1,12,470 lakh" or "11247.0" in the source fails subset → the 0.95 gate rejects a *correct* number, blocking legitimate fields.
**Why it happens:** Lakh/crore/million unit shifts and decimal-vs-integer formatting are pervasive in DRHP financials; the antibody was tuned for "swapped number" detection, not unit reconciliation.
**How to avoid:** In Pattern 6, add unit-aware (lakh×1e5, crore×1e7, million×1e6) + tolerance reconciliation before declaring a number ungrounded. Test on real Swiggy figures (revenue 11,247 cr; OFS 4,499 cr) from the existing gold set.
**Warning signs:** Gate fails on fields you can manually verify in the DRHP; numeric_faithfulness mysteriously < 0.9 on hand-verified Qs.

### Pitfall 2: Risk-factor boilerplate inflates the risk story (P12 — phase-owned)
**What goes wrong:** With n≈8, IDF is noisy; near-identical merchant-banker boilerplate ("dependent on Indian macroeconomic conditions") can score mid-band and crowd out genuine issuer-specific risks.
**Why it happens:** 60–80% phrase overlap across DRHPs; unigram IDF under-penalizes phrase-level boilerplate; small N.
**How to avoid:** Phrase-level (n-gram/shingle) IDF + the hand-curated boilerplate floor (D3-14) as a deterministic clamp. Evaluate on issuer-specific recall, not gross recall (PITFALLS P12 #3). Document n≈8 honestly.
**Warning signs:** Top-ranked risks across two IPOs are near-identical strings; inter-IPO overlap of "issuer-specific" risks > 50%.

### Pitfall 3: Evaluation theater on the F1 numbers (P10 — phase-owned)
**What goes wrong:** Committing "RPT F1: 0.82" with no interpretation, no failure inspection, no confidence-bucket split → can't answer "what does 0.82 miss?".
**Why it happens:** Metrics are cheaper to compute than to interpret; single-labeler small-n F1 looks authoritative.
**How to avoid:** Every field metric gets an interpretation paragraph (P10 #1); report F1 split by confidence bucket (D3-04); commit the honest n (D3-05); include ≥a few inspected failure cases (the Phase-6 failure gallery is deferred, but Phase 3 should seed inspected examples per P10).
**Warning signs:** The committed report is a bare metric table; no "what these mean" prose; confidence is decorative not measured.

### Pitfall 4: The release gate prints but doesn't enforce
**What goes wrong:** `make release` computes 0.93 and still lets the deploy proceed (prints a warning) — "enforcement over discipline" (Specific Ideas) is violated.
**Why it happens:** Easy to `print()` a number; harder to wire a real non-zero exit + block.
**How to avoid:** `release_gate.py` must `sys.exit(1)` below threshold; the `Makefile` target must fail the build (Make stops on non-zero). The offline fixture test asserts the exit behavior at 0.94 and 0.96 (D3-12).
**Warning signs:** No `tests/eval/test_release_gate.py`; the gate has no negative-path test.

### Pitfall 5: Methodology pane silently triggers a live call (D3-17 violation)
**What goes wrong:** The pane re-runs retrieval or recomputes an eval score per expansion → slow, costly, non-reproducible.
**Why it happens:** It's tempting to "just call the agent" to get chunks/scores at render time.
**How to avoid:** Persist the per-claim trace (query + chunk list + scores) into `RedFlagRecord` at precompute; read eval scores from the latest committed report file. The pane is pure rendering (Pattern 8).
**Warning signs:** Expanding the pane is slow; eval scores differ between two expansions; an LLM/Qdrant client import appears in the UI module.

### Pitfall 6: Confidence conflated with absence (D3-03 violation)
**What goes wrong:** A "Not disclosed in DRHP" field is rendered as "low confidence", or hidden entirely.
**Why it happens:** Both feel like "we don't have a good value".
**How to avoid:** Absence is a `RefusalResponse` with NO confidence label (UI-SPEC: confidence label omitted for not-disclosed rows); the row still renders. Confidence is only for *present* values.
**Warning signs:** A not-disclosed row shows "Confidence: low"; a field with no value is missing from the table.

## Code Examples

### Mirror the snapshot precompute loop for red-flag extraction
```python
# Source: pipelines/snapshot.py:92-166 (verified existing) — adapt for 7 red-flag queries
from agent.graph import GRAPH
from compliance.scrubber import scrub
from agent.schemas import RefusalResponse

def precompute_redflags(drhp_id: str, *, write: bool = True) -> RedFlagRecord:
    fields: dict[str, RedFlagField] = {}
    for field_key, query in REDFLAG_QUERIES.items():
        state = GRAPH.invoke({"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0})
        ga, refusal = state.get("grounded_answer"), state.get("refusal")
        if ga is not None and scrub(ga.answer_prose).passed:
            tier, score = classify_confidence(ga)          # deterministic rubric (D3-01)
            fields[field_key] = RedFlagField(value=ga, confidence_tier=tier, confidence_score=score)
        else:
            value = refusal or RefusalResponse(reason="unsupported_claim",
                                               explanation="Not disclosed in DRHP",
                                               reformulation_suggestions=[])
            fields[field_key] = RedFlagField(value=value)   # no confidence on absence (D3-03)
    # field #2 reuses the already-computed OFS/fresh split rather than re-extracting:
    # ofs = compute_ofs_fresh(snapshot.fields["use_of_proceeds"])  # from pipelines/snapshot.py
    ...
```

### The numeric-subset antibody already present (extend this)
```python
# Source: agent/nodes/cite_check.py:53-71 (verified existing) — EXTEND with unit/tolerance reconciliation
def _extract_numbers(s: str) -> set[str]:
    s_no_commas = re.sub(r"(\d),(\d)", r"\1\2", s)   # strips Indian thousands commas already
    return set(re.findall(r"\d+(?:\.\d+)?", s_no_commas))
def _numbers_subset(claim_numbers, window_numbers) -> bool:
    if not claim_numbers: return True
    return claim_numbers.issubset(window_numbers)     # <-- exact-string; Phase 3 adds lakh/crore + tolerance
```

### Per-field-type F1 (set-overlap leg with rapidfuzz)
```python
# rapidfuzz is already a dependency (requirements.txt). Set-overlap F1 for list fields:
from rapidfuzz import fuzz
def set_overlap_f1(pred: list[str], gold: list[str], thresh: int = 85) -> float:
    matched = sum(1 for g in gold if any(fuzz.token_set_ratio(g, p) >= thresh for p in pred))
    if not pred and not gold: return 1.0
    prec = matched / len(pred) if pred else 0.0
    rec  = matched / len(gold) if gold else 0.0
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
```

## State of the Art

| Old Approach | Current Approach (this phase) | When Changed | Impact |
|--------------|------------------------------|--------------|--------|
| LLM self-reported confidence | Deterministic source-grounding rubric (D3-01) | Phase 3 decision | Defensible, free, anchored to citations. |
| Page-level / prose number emission | Per-number grounding gate inside cite_check (D3-10) | Phase 3 (extends Phase 1 antibody) | A hallucinated number is blocked, not displayed. |
| Gross risk recall | IDF + boilerplate-floor issuer-specific ranking (D3-14, P12) | Phase 3 | Issuer-specific risks foregrounded; boilerplate doesn't inflate metrics. |
| Live "explain this" recomputation | Cached claim_id trace + committed eval report (D3-17) | Phase 3 | Fast, cheap, reproducible methodology pane. |

**Deprecated/outdated:**
- The PyPI package `sklearn` (bare name): deprecated shim — always use `scikit-learn`. (Relevant only if the planner overrides the stdlib-IDF recommendation.)

## Project Constraints (from CLAUDE.md)

- **Free/minimal-tier only** — no paid feeds, deploy must stay near-zero cost. → No new heavy dependency on the free HF Space; stdlib IDF over sklearn; cached precompute over request-time LLM.
- **Honesty-first / no-advice** — banned-token scrubber applies to ALL red-flag/risk/methodology copy (UI-SPEC L3-8); new user-facing strings go in `ui/copy.py` under the import-time scrubber assertion. No "subscribe/avoid/buy/sell/target/recommend/fair value".
- **No green/red coding, no badges, no severity icons** — confidence labels, specificity words, field values, IDF meter all monochrome (UI-SPEC L3-1).
- **DS depth visible as artifacts** — committed gold set + per-field F1 + labeling rubric + numeric gate + interpretation paragraphs (this phase is a core DS-rigor surface; P10/P11).
- **Indian-context formatting** (lakh/crore, ₹, %) — load-bearing for the numeric gate's normalization (Pattern 6) and required for correct display (UI-04 is Phase 4, but numeric normalization is needed here).
- **GSD workflow enforcement** — all edits go through a GSD command; atomic per-task commits; pytest stubs flip stub→green per wave.
- **Storage is the integration bus** — batch pipelines write caches, on-demand UI reads; no pipeline calls the agent at request time; the red-flag pipeline writes, the snapshot page reads.
- **Span-level citations, non-LLM cite-check before emit** — every red-flag value carries claim_id citations; cite_check (no LLM imports) validates before caching.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | stdlib TF-IDF over n≈8 risk sections is sufficient (no sklearn) | Standard Stack / Pattern 4 | If IDF quality is poor at n=8, may need better weighting; the boilerplate floor mitigates. Verify empirically per D3-14. |
| A2 | Reuse-the-grounded-pipeline yields clean structured red-flag values without a dedicated extraction schema | Pattern 1 (discretion) | If canned queries don't reliably surface (e.g.) RPT% as a parseable number, a light post-parse or a targeted prompt may be needed. Default is reuse; fall back to a parse step, not a new claim-less path. |
| A3 | The per-claim retrieval trace needed by the methodology pane can be captured into the cache at precompute time | Pattern 8 | If `state["reranked_top_k"]` / the query aren't persisted, the pane would need a live call (violates D3-17). Verify what's retained and persist the minimum. |
| A4 | Numeric tolerance + lakh/crore reconciliation makes the 0.95 gate achievable on the ingested set | Pattern 6 / Pitfall 1 | If the gate can't clear 0.95 even after normalization, the field/eval-set scope or tolerance must be re-tuned (document the procedure). |
| A5 | `scikit-learn` latest = 1.9.0 (2026-06-02) | Standard Stack | Only matters if sklearn is adopted (not recommended); verify at install time. |
| A6 | Right-sizing gold-set n to currently-ingested DRHPs (likely just `swiggy_2024_11` until live ingest) is acceptable per D3-05 | Runtime State Inventory | If only 1 DRHP is ingested, F1 n is tiny; D3-05 explicitly allows honest small-n with 20-30 documented as target. The phase must not block on full ingest. |

## Open Questions

1. **How many DRHPs are actually ingested into live Qdrant at Phase 3 start?**
   - What we know: only `swiggy_2024_11` is seeded (hand-placeholder per STATE.md); the other 7 catalogue IPOs await live ingest (`data/INGEST_ALL_LATER.md`, Phase 2 carry-over). F1 requires the extractor to RUN on each labeled DRHP (D3-05 coupling).
   - What's unclear: whether the planner schedules a partial live-ingest of a few more DRHPs within Phase 3 to make F1 meaningful (n>1), or right-sizes to whatever is ingested.
   - Recommendation: plan an early "ingest the gold-set DRHPs" wave (extend `pipelines/ingest.py` loop, the discretion option), targeting enough DRHPs for an honest F1; report true n; keep 20-30 as the documented target.

2. **Does the cached structure already retain the retrieval query + full chunk list for the methodology pane?**
   - What we know: `claim.sources[]` carries score/section/span; the canned query is known per field; `state["reranked_top_k"]` exists at runtime.
   - What's unclear: whether the full reranked chunk list (beyond the cited sources) is persisted anywhere after precompute.
   - Recommendation: during the redflag-schema task, decide the minimum trace to persist (query + the cited sources' scores are likely enough for the UI-SPEC pane); avoid over-persisting full chunk text to keep the cache small.

3. **Per-field numeric tolerances and IDF band thresholds.**
   - What we know: D3-07/D3-14 leave these to empirical tuning, documented in the rubric.
   - What's unclear: exact values (e.g. ±0.5pp for %, ± rounding for amounts; IDF percentile cutoffs for the 3 bands).
   - Recommendation: tune against the labeled set, commit the chosen values + procedure into `extraction_rubric.md`; treat thresholds as calibration constants (mirror `agent/policies.py`'s single-source-of-truth posture).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `rapidfuzz` | set-overlap F1, IDF boilerplate match | ✓ (vendored, tests green) | present | — |
| `pydantic` v2 | RedFlagRecord schema | ✓ | >=2.7,<3 | — |
| `streamlit` | methodology pane / red-flag rows | ✓ | >=1.36 | — |
| Live Qdrant + Gemini/Groq keys | red-flag extraction + numeric eval track + `make release` | ✗ at research time (keys not in this env) | — | offline unit tests monkeypatch `GRAPH.invoke` (the CODE-NOW-DEFER pattern); live run deferred to runbook |
| `scikit-learn` | (only if sklearn IDF adopted — NOT recommended) | ✗ | 1.9.0 on PyPI | stdlib TF-IDF (recommended path) |
| `slopcheck` | package legitimacy audit | ✗ | — | all-`[ASSUMED]` degradation applied (only the optional sklearn is new) |

**Missing dependencies with no fallback:** None for the recommended path (no new package). Live infra (Qdrant + LLM keys) is required only for the real precompute / numeric-gate run, which — consistent with the Phase 1/2 CODE-NOW-DEFER pattern — is deferred to the ingest runbook; all gate/scorer **logic** is offline-unit-testable.

**Missing dependencies with fallback:** sklearn (→ stdlib IDF, recommended anyway); live infra (→ monkeypatched offline tests for everything except the final live numeric run).

## Validation Architecture

> nyquist_validation is enabled (`workflow.nyquist_validation: true` in config.json). Section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest>=8` `[VERIFIED: pyproject.toml [project.optional-dependencies].dev]` |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `--strict-markers`, `slow` marker) |
| Quick run command | `pytest tests/unit -q` (offline, monkeypatched — the established fast path) |
| Full suite command | `pytest -q` (237+ unit tests baseline + new Phase 3 tests) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXTRACT-01 | 7-field red-flag record built from canned queries; not-disclosed → RefusalResponse | unit (monkeypatch `GRAPH.invoke`) | `pytest tests/unit/test_redflag_precompute.py -x` | ❌ Wave 0 |
| EXTRACT-01 | RedFlagRecord round-trips to/from JSON (union discriminator) | unit | `pytest tests/unit/test_redflag_schema.py -x` | ❌ Wave 0 |
| EXTRACT-02 | confidence rubric: verbatim→high, light-parse→medium, cross-section→low; absence→no label | unit | `pytest tests/unit/test_confidence_rubric.py -x` | ❌ Wave 0 |
| EXTRACT-03 | per-field-type F1: numeric tolerance / boolean exact / set-overlap; refusal scored, not dropped | unit | `pytest tests/eval/test_extraction_f1.py -x` | ❌ Wave 0 |
| EXTRACT-03 | F1 split by confidence bucket (D3-04) | unit | `pytest tests/eval/test_extraction_f1.py::test_bucket_split -x` | ❌ Wave 0 |
| EVAL-03 | numeric grounding: lakh/crore/₹ reconciliation + tolerance; ungrounded number → blocked | unit | `pytest tests/unit/test_numeric_grounding.py -x` | ❌ Wave 0 |
| EVAL-03 | release gate exits non-zero at 0.94, passes at 0.96 (offline fixture) | unit | `pytest tests/eval/test_release_gate.py -x` | ❌ Wave 0 |
| P12 | IDF ranks issuer-specific above boilerplate; floor clamps known boilerplate | unit | `pytest tests/unit/test_risk_idf.py -x` | ❌ Wave 0 |
| METHOD-01 | pane renders from cached trace + committed report; no LLM/Qdrant import in UI module | unit (`inspect.getsource` substring check, mirror `test_no_llm_judge_fallback`) | `pytest tests/unit/test_methodology_pane.py -x` | ❌ Wave 0 |
| EXTRACT-01/02 | snapshot page boots with red-flag block for seeded IPO | smoke | `bash scripts/smoke.sh` (extend to assert red-flag route) | ✓ (extend) |

### Sampling Rate
- **Per task commit:** `pytest tests/unit -q` (fast, offline, monkeypatched)
- **Per wave merge:** `pytest -q` (full offline suite)
- **Phase gate:** full suite green **and** `make release` ≥0.95 on the numeric track (live) before `/gsd-verify-work`; the committed extraction-F1 + numeric-gate reports exist under `eval/reports/`.

### Wave 0 Gaps
- [ ] `tests/unit/test_redflag_schema.py` — RedFlagRecord round-trip (EXTRACT-01)
- [ ] `tests/unit/test_redflag_precompute.py` — monkeypatched 7-query loop (EXTRACT-01)
- [ ] `tests/unit/test_confidence_rubric.py` — deterministic tiers (EXTRACT-02)
- [ ] `tests/eval/test_extraction_f1.py` — per-field-type + bucket-split scorer (EXTRACT-03)
- [ ] `tests/unit/test_numeric_grounding.py` — lakh/crore/tolerance reconciliation (EVAL-03)
- [ ] `tests/eval/test_release_gate.py` — gate exit-code behavior at 0.94/0.96 (EVAL-03)
- [ ] `tests/unit/test_risk_idf.py` — ranking + boilerplate floor (P12)
- [ ] `tests/unit/test_methodology_pane.py` — cached-only render + no-live-call assertion (METHOD-01)
- [ ] Shared fixtures: a synthetic `RedFlagRecord` + a tiny labeled `extraction_labels.jsonl` fixture + a 3-doc IDF corpus fixture (extend `tests/eval/` conftest)
- [ ] No new framework install — pytest already present.

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high` in config.json. Section included.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user accounts in v1 (REQUIREMENTS Out of Scope: no login/personalization). |
| V3 Session Management | no | Stateless read-only Streamlit app; no durable user session (LangGraph checkpointer for chat memory only). |
| V4 Access Control | partial | The `is_known_drhp_id` allow-list (Phase 2, `data/catalogue_loader.py`, enforced inside `retrieve.run`) bounds which DRHPs can be queried — Phase 3 must reuse it for any `drhp_id` reaching the red-flag pipeline/cache reader (no arbitrary id → arbitrary cache path). |
| V5 Input Validation | yes | Pydantic schemas (`RedFlagRecord`, reused `GroundedAnswer`/`Claim` with the `claim_id` regex + span-offset validator) validate all cached/loaded data. `drhp_id` must be allow-list-checked before forming a cache file path (path-traversal guard). |
| V6 Cryptography | no | No new secrets; no crypto. Reuse existing `_check_env` for API keys (never hard-coded). |

### Known Threat Patterns for {Streamlit + offline-precompute + cached JSON}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `drhp_id` path traversal into the cache reader (`data/redflag/<id>.json`) | Tampering | Validate `drhp_id` against `is_known_drhp_id` allow-list (reuse Phase 2 guard) before constructing any path; never interpolate raw user input into a file path. |
| Hallucinated/ungrounded number reaches the user as fact | Information disclosure / Repudiation | Per-number grounding gate (D3-10) blocks ungrounded numbers → RefusalResponse; numeric_faithfulness ≥0.95 release gate (the phase's core security-of-truth control). |
| Banned/prescriptive token surfaces in red-flag/risk/pane copy | (compliance/regulatory — SEBI RIA boundary, PITFALLS P1) | Banned-token scrubber on all generated red-flag prose AND new UI copy via `ui/copy.py` import-time assertion (UI-SPEC L3-8); defense-in-depth scrub in the precompute loop (mirror `snapshot.precompute`). |
| Corrupted span offsets (start>end) reaching cite-check window | Tampering | Already mitigated by the `span_offsets` validator in `schemas.py` (STRIDE T-1-02) — reused unchanged. |
| Inverted IDF meter implying "more fill = more dangerous" | (UX-as-advice, P21) | UI-SPEC fixes meter direction (more fill = more issuer-specific, not a verdict); monochrome, accompanied by text % (WCAG 1.4.1). |

## Sources

### Primary (HIGH confidence)
- Repo code (verified by direct read): `agent/schemas.py`, `agent/snapshot_schema.py`, `agent/nodes/cite_check.py`, `pipelines/snapshot.py`, `pipelines/snapshot_queries.py`, `scripts/run_eval.py`, `scripts/smoke.sh`, `agent/policies.py`, `data/catalogue.json`, `requirements.txt`, `pyproject.toml` — the contracts and patterns Phase 3 extends.
- Planning docs (verified): `03-CONTEXT.md` (D3-01..D3-17), `03-UI-SPEC.md` (L3-1..L3-9, R-1/2/3), `REQUIREMENTS.md` (EXTRACT/EVAL/METHOD), `ROADMAP.md` (Phase 3 SC1-6, pitfalls P2/P10/P12), `STATE.md`, `research/PITFALLS.md` (P2, P10, P12 prevention specifics), `config.json`.

### Secondary (MEDIUM confidence)
- [scikit-learn · PyPI](https://pypi.org/project/scikit-learn/) and [Installing scikit-learn 1.9.0 docs](https://scikit-learn.org/stable/install.html) — latest = 1.9.0 (2026-06-02); only relevant if sklearn is adopted (not recommended).
- [sklearn · PyPI](https://pypi.org/project/sklearn/) — confirms the bare `sklearn` name is a deprecated shim; use `scikit-learn`.

### Tertiary (LOW confidence)
- None — every load-bearing claim is grounded in repo code or a primary planning doc.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new core lib; reuses already-vendored, test-green dependencies; sklearn version verified on PyPI.
- Architecture: HIGH — every pattern is a direct mirror/extension of verified existing code (snapshot pipeline, cite_check, run_eval, SnapshotRecord).
- Pitfalls: HIGH — drawn from the committed PITFALLS.md (P2/P10/P12) plus a code-verified gotcha (exact-string `_numbers_subset` will false-fail on lakh/crore).
- IDF approach (Pattern 4): MEDIUM — the algorithm is standard but its quality at n≈8 is empirical (A1); the boilerplate floor de-risks it.

**Research date:** 2026-06-25
**Valid until:** ~2026-07-25 (stable; the locked stack and repo contracts are slow-moving. Re-verify sklearn version only if it is adopted.)
</content>
</invoke>
