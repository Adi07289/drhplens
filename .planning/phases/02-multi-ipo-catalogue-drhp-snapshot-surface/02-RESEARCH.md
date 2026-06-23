# Phase 2: Multi-IPO Catalogue + DRHP Snapshot Surface - Research

**Researched:** 2026-06-23
**Domain:** Generalizing Phase 1's single-IPO RAG pipeline to N IPOs; offline snapshot pre-computation; catalogue + snapshot data model; multi-DRHP ingestion robustness on Indian DRHPs
**Confidence:** HIGH on ingestion generalization (verified directly against Phase 1 code), HIGH on DRHP source URLs (all 8 confirmed on SEBI), HIGH on snapshot architecture (reuses verified Phase 1 schema), MEDIUM on P13 hybrid-retrieval scope (the right call depends on Phase-1 recall numbers that don't exist yet — gold-set is 13 entries, eval not yet run live)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**IPO Catalogue**
- **D2-01:** Curate ~8 recent recognizable mainboard IPOs: Swiggy (already ingested), plus a verified subset of Hyundai Motor India, Ola Electric, Zomato, Nykaa, Paytm, LIC, Mamaearth. Planner/executor MUST verify each has a publicly downloadable DRHP on SEBI/BSE/NSE before committing it to the catalogue; substitute a comparable recognizable IPO if a DRHP is unavailable. Deliberate mix of winners (Zomato, Hyundai) and disappointments (Paytm, LIC, Ola).
- **D2-02:** Each catalogue IPO requires: DRHP PDF + SHA-256 pin (same pattern as Swiggy), offline ingestion into the same Qdrant collection (drhp_id discriminator), and offline snapshot pre-computation.

**Snapshot Computation**
- **D2-03:** Snapshot fields are pre-computed offline at ingestion time. Each field computed once, cached to a relational/JSON store keyed by drhp_id, rendered on demand. Re-uses the Phase 1 `GroundedAnswer`/`Claim` schema so every snapshot field carries `claim_id` citations.
- **D2-04:** Snapshot extraction reuses the Phase 1 retrieval + generate + cite_check pipeline (not a new LLM path). Each field block is a targeted query against that IPO's chunks, run through the same grounding + cite-check guarantees. The banned-token scrubber applies to all snapshot copy.

**Snapshot Field Blocks (SNAP-02..07)**
- **D2-05:** Six cited field blocks per IPO: (1) metadata header (SNAP-02); (2) plain-English business summary (SNAP-03); (3) key financials snapshot (SNAP-04); (4) prioritized risk-factors summary (SNAP-05); (5) use-of-proceeds breakdown (SNAP-06); (6) promoter/management section (SNAP-07).
- **D2-06:** The OFS-vs-fresh-issue split is visually foregrounded in use-of-proceeds.

**Catalogue + Snapshot UI**
- **D2-07:** Catalogue = browseable grid/list of IPO cards → click → snapshot page. Reuse Phase 1 design system. No green/red coding.
- **D2-08:** Snapshot page renders the Q&A chat (Phase 1) alongside or below the 6 field blocks — same IPO context.

### Claude's Discretion (planner resolves)
- Exact catalogue IPO final list (after DRHP-availability verification)
- Snapshot field block layout (cards vs accordion vs sections) — defer to UI-SPEC
- Relational store choice for cached snapshots (SQLite vs JSON files committed to repo) — SQLite preferred for query, JSON acceptable for simplicity
- Whether the catalogue metadata is hand-curated JSON or scraped (hand-curated is fine for ~8 IPOs in v1)

### Deferred Ideas (OUT OF SCOPE)
- Cross-IPO side-by-side comparison — v2 (E3 / MULTI-IPO-COMPARE-01)
- Red-flag extraction table — Phase 3 (EXTRACT-01..03)
- Peer multiples / GMP — Phase 4
- Full Indian-context formatting (lakh/crore everywhere, RPT/QIB/NII/RII tooltips) — Phase 4 (UI-04); Phase 2 only does issue-size lakh/crore
- Automated DRHP ingestion from SEBI feeds — v2 (AUTO-INGEST-01)
- User-uploadable DRHP — v2 (E5); Phase 2's ingestion generalization keeps this unblocked
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SNAP-01 | User can browse the list of covered mainboard IPOs | §4 catalogue data model (`data/catalogue.json`); §2 DRHP sourcing |
| SNAP-02 | Per-IPO metadata — price band, lot size, dates, issue size, fresh vs OFS, lead managers | §3 + §5 — metadata block: retrieve cover page + "The Issue"/"General Information"; mostly cover-page extraction |
| SNAP-03 | Plain-English business-model summary, DRHP-cited | §3 + §5 — retrieve "Our Business" + "Industry Overview"; reuse generate node |
| SNAP-04 | Key-financials snapshot (3-5 yr revenue/profit/margins/debt/ROE/ROCE) | §3 + §5 — retrieve "Restated Financial Statements" + "Financial Information"; P2 numeric-faithfulness applies |
| SNAP-05 | Prioritized risk-factors summary, each cluster citing DRHP risk text | §3 + §5 — retrieve "Risk Factors"; P13 (boilerplate) noted but full IDF-dedup is Phase 3 |
| SNAP-06 | Use-of-proceeds breakdown with OFS-vs-fresh % highlighted | §3 + §5 — retrieve "Objects of the Issue" + "The Issue"; OFS split foregrounded (D2-06) |
| SNAP-07 | Promoter/management section (names, pre/post holdings, pledging, prior matters) | §3 + §5 — retrieve "Our Promoters" + "Capital Structure" + "Our Management" |
| OPS-01 | v1 covers 5-10 recent mainboard IPOs + 1-2 currently-open | §2 — 8 confirmed SEBI sources; "currently-open" handling discussed in Open Questions |
</phase_requirements>

## Summary

Phase 2 is **breadth, not new depth**. Every LLM path, schema, retrieval primitive, cite-check, scrubber, and citation renderer already exists and is verified in Phase 1's 219-test codebase. Phase 2 does exactly four things: (1) parameterize the single hard-coded `drhp_id` so the pipeline and the agent can address any of N IPOs; (2) source and ingest ~7 more DRHPs; (3) pre-compute 6 cited snapshot blocks per IPO offline and cache them; (4) add a catalogue browser + snapshot page to the Streamlit multipage app (UI deferred to 02-UI-SPEC.md, out of scope here).

The single most important code finding: **the entire multi-IPO machinery already exists except for two hard-codes.** `storage/vector.py::search()` already takes `drhp_id` as a required parameter and filters Qdrant on it with a payload index — multi-IPO retrieval is *already correct at the storage layer*. The only blockers are (a) `agent/nodes/retrieve.py` imports `DRHP_ID_DEFAULT` and passes it instead of reading from graph state, and (b) `app.py` invokes the graph without a `drhp_id` key. Threading `drhp_id` through `GraphState` + `intake` + `retrieve` and into the two snapshot/chat call sites is the whole generalization. This is a small, surgical change — not a refactor.

Snapshot pre-computation is "run the existing agent 6 times per IPO with 6 canned queries, store the 6 resulting `GroundedAnswer` objects." Because `GroundedAnswer` already carries `claim_id`-bearing `Claim` objects with page anchors, the cache record *is* a serialized `GroundedAnswer` per field — citations propagate for free. **Recommendation: cache as JSON-per-IPO committed to the repo** (`data/snapshots/<drhp_id>.json`), not SQLite — rationale in §3. This matches the existing "commit the docling.json artifact" pattern, makes snapshots diff-reviewable in git, and needs zero new query infrastructure for ~8 IPOs.

**Primary recommendation:** Walking-skeleton order — (Wave 0) thread `drhp_id` through state + write `pipelines/ingest.py(drhp_id, pdf_path, ...)` + `data/catalogue.json` schema with 2 IPOs (Swiggy + Hyundai); (Wave 1) snapshot pre-compute pipeline producing 1 field (metadata) for 1 IPO end-to-end, cached + rendered; (Wave 2) scale to all 6 field blocks for those 2 IPOs; (Wave 3) ingest the remaining IPOs + handle parse failures gracefully (P14). Defer the BM25-hybrid retrieval upgrade (P13) to a tail wave **gated on measured recall** — do not build it speculatively.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DRHP acquisition (N PDFs) | Build-time (local/CI script) | — | SEBI URLs stable for filed docs; SHA-pin + mirror per IPO (P14) |
| DRHP parsing + chunk + embed (N IPOs) | Build-time (offline batch) | Cached docling.json committed | Same as Phase 1; now looped over drhp_id |
| Vector storage (multi-IPO) | External SaaS (Qdrant Cloud) | — | **Already multi-IPO ready** — `search(drhp_id=...)` filters on payload index |
| Snapshot pre-computation (6 blocks × N) | Build-time (offline batch) | Gemini/Groq APIs | Avoids 6 LLM calls per page view (D2-03); writes JSON cache |
| Snapshot cache storage | Repo-committed JSON (`data/snapshots/`) | — | Diff-reviewable; no runtime query infra needed for ~8 IPOs |
| Catalogue metadata | Repo-committed JSON (`data/catalogue.json`) | — | Hand-curated; ~8 IPOs (D2: "hand-curated is fine") |
| Catalogue page render | Streamlit Server (HF Spaces) | — | Reads catalogue.json; renders cards (UI-SPEC) |
| Snapshot page render | Streamlit Server (HF Spaces) | — | Reads snapshot JSON; renders 6 blocks + reuses chip renderer |
| Per-IPO Q&A (on snapshot page) | Streamlit Server (in-process) | Gemini/Groq APIs | **Existing graph**, now invoked with the page's `drhp_id` |
| `drhp_id` selection | Streamlit Server (session state) | — | Catalogue click sets `st.session_state["drhp_id"]` → passed to graph + snapshot loader |

## Standard Stack

**No new libraries.** Phase 2 is built entirely on the Phase 1 stack (locked in CLAUDE.md / STACK.md). The ingestion path additionally activates real Docling now that Python 3.11 is available (Phase 1 fell back to PyMuPDF on 3.13 per `data/swiggy_drhp/INGEST_LATER.md`).

### Core (all already installed in Phase 1)
| Library | Version | Purpose in Phase 2 | Why Standard |
|---------|---------|--------------------|--------------|
| `docling` | `>=2.95,<3` | Parse the 7 new DRHPs (real Docling now; Python 3.11 enables it) | Locked Phase 1 [CITED: CLAUDE.md] |
| `qdrant-client` | `>=1.18,<2` | Same collection, new drhp_ids (no schema change) | Locked; payload filter verified in `storage/vector.py` |
| `sentence-transformers` (bge-m3) | `>=3` | Embed new IPOs' chunks; embed snapshot-query strings | Locked Phase 1 |
| `instructor` + `pydantic` | locked | Snapshot extraction reuses `GroundedAnswer` response_model | Already the generate-node contract |
| `langgraph` | `>=1.2,<2` | Snapshot pre-compute calls the existing compiled graph | No graph changes needed |
| `streamlit` | `>=1.36` | Catalogue page + snapshot page (multipage `pages/`) | Locked; `pages/01_methodology.py` precedent exists |
| `typer` + `rich` | locked | Generalized `pipelines/ingest.py` CLI + snapshot CLI | Matches `ingest_swiggy.py` pattern |
| `tiktoken` | locked | Chunk token counting (unchanged) | Already used in chunker |

### Conditionally activated (only if P13 recall measurement justifies it — see §6)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rank_bm25` | `0.2.2` | Sparse BM25 leg for hybrid retrieval | **Only if** measured recall@10 on Indian-finance queries is below threshold. CLAUDE.md lists it; Qdrant native sparse vectors are the alternative (no extra index). |
| `FlagEmbedding` (bge-reranker-v2-m3) | latest | Already in Phase 1 rerank node | Already used — confirm it's in the rerank path; no new install |

**Installation:** No new install for the core path. If hybrid retrieval is approved in a tail wave:
```bash
# Already in CLAUDE.md stack; verify before adding
pip index versions rank_bm25   # confirm 0.2.2 on PyPI
# Prefer Qdrant native sparse vectors (v1.10+) to avoid a second index entirely
```

**Version verification:** No new packages → no new registry verification required. All Phase 2 packages were verified in `01-RESEARCH.md` §Package Legitimacy Audit and are pinned in the existing `pyproject.toml`/`requirements.txt`.

## Package Legitimacy Audit

**Not applicable — Phase 2 installs no new external packages.** Every library is already present in the Phase 1 dependency set (audited in `01-RESEARCH.md`). The one conditional addition (`rank_bm25`) is already listed in CLAUDE.md's authoritative stack (8+ year track record, `dorianbrown/rank_bm25`, pure-Python, no postinstall scripts). If the planner approves the hybrid-retrieval tail wave, run `slopcheck install rank_bm25 --json` before adding it; otherwise prefer Qdrant native sparse vectors and add nothing.

## Architecture Patterns

### System Architecture Diagram

```
   BUILD-TIME (offline, per drhp_id, looped over catalogue)
   ┌──────────────────────────────────────────────────────────────────────┐
   │                                                                        │
   │  data/catalogue.json ──(drives the loop)──┐                            │
   │                                            ▼                           │
   │  DRHP PDF (SEBI URL + SHA-256 pin) ──► pipelines/ingest.py(            │
   │   data/<drhp_id>/<file>.pdf                drhp_id, pdf_path, metadata) │
   │                                            │                           │
   │                                            ▼                           │
   │              ┌── Docling parse → docling.json (committed) ──┐          │
   │              │   section-aware chunk → bge-m3 embed         │          │
   │              │   upsert to Qdrant (payload.drhp_id = <id>)  │          │
   │              └───────────────────────────────────────────────┘          │
   │                                            │                           │
   │                                            ▼                           │
   │  pipelines/precompute_snapshot.py(drhp_id)                             │
   │   for field in [metadata, business, financials, risks,                 │
   │                 use_of_proceeds, promoter]:                            │
   │       query = SNAPSHOT_QUERIES[field]                                  │
   │       state = GRAPH.invoke({question: query, drhp_id: <id>})  ◄────────┼── reuses
   │       grounded_answer = state["grounded_answer"]   (claim_ids!)        │   Phase 1
   │   write data/snapshots/<drhp_id>.json {field: GroundedAnswer, ...}     │   agent
   └──────────────────────────────────────────────────────────────────────┘
                              │                              │
                              ▼                              ▼
                  ┌────────────────────┐         ┌────────────────────┐
                  │   Qdrant Cloud     │         │ data/snapshots/    │
                  │  drhp_chunks       │         │  <drhp_id>.json     │
                  │  (all IPOs, 1 coll)│         │  (committed)        │
                  └────────────────────┘         └────────────────────┘
                              ▲                              │
   RUNTIME (HF Spaces)        │ ANN query (drhp_id filter)   │ read
   ┌──────────────────────────┼──────────────────────────────┼─────────────┐
   │  pages/catalogue.py      │                              │             │
   │   reads catalogue.json → renders IPO cards              │             │
   │        │ click sets st.session_state["drhp_id"]         │             │
   │        ▼                                                │             │
   │  pages/snapshot.py?drhp_id=<id>                         ▼             │
   │   ├─ reads data/snapshots/<id>.json → renders 6 cited blocks         │
   │   │   (reuses ui/ citation chip + expander renderers)                │
   │   └─ Q&A chat: GRAPH.invoke({question, drhp_id: <id>}) ──────────────┤
   │       (same per-IPO context — D2-08)                                 │
   └─────────────────────────────────────────────────────────────────────┘
```

### Pattern 1: drhp_id Threaded Through Graph State (THE generalization)

**What:** Replace the single hard-coded `DRHP_ID_DEFAULT` read in `retrieve.py` with a `drhp_id` value carried in `GraphState`, supplied by the caller.

**Verified current state (read directly from code):**
- `storage/vector.py::search(query_vector, drhp_id, limit)` — **already** takes `drhp_id` and filters Qdrant via `FieldCondition(key="drhp_id", match=...)`, backed by a KEYWORD payload index (`ensure_collection` creates it). **No storage change needed.** ✅
- `agent/nodes/retrieve.py` line 9/32 — imports `DRHP_ID_DEFAULT` and passes `drhp_id=DRHP_ID_DEFAULT`. **This is the line to change.** Its own docstring says: *"Phase 2 will introduce dynamic drhp_id selection."*
- `agent/state.py::GraphState` — TypedDict has no `drhp_id` key. **Add one.**
- `agent/nodes/intake.py` — initializes all state keys; should pass `drhp_id` through.
- `app.py` (~line 278) — `graph.invoke({"question": ..., "regenerate_attempts": 0})` — **add `"drhp_id": st.session_state["drhp_id"]`.**
- `agent/policies.py::DRHP_ID_DEFAULT` — keep as a *fallback default* for backward compat / tests, not deleted.

**Concrete change set:**
```python
# agent/state.py — add to GraphState TypedDict
class GraphState(TypedDict):
    question: str
    drhp_id: str           # NEW: which IPO this query targets
    retrieved_chunks: list[dict]
    # ... rest unchanged

# agent/nodes/intake.py — preserve/default drhp_id
from agent.policies import DRHP_ID_DEFAULT
def run(state: GraphState) -> GraphState:
    question = state.get("question", "").strip()
    drhp_id = state.get("drhp_id") or DRHP_ID_DEFAULT   # fallback keeps Phase-1 tests green
    return {**state, "question": question, "drhp_id": drhp_id, ...}

# agent/nodes/retrieve.py — read from state, not the constant
def run(state: GraphState) -> GraphState:
    hits = search(
        query_vector=embed_query(state["question"]),
        drhp_id=state["drhp_id"],     # was: DRHP_ID_DEFAULT
        limit=RETRIEVE_LIMIT,
    )
    return {**state, "retrieved_chunks": hits}

# app.py + snapshot pre-compute — supply drhp_id at the call site
result_state = graph.invoke({
    "question": question,
    "drhp_id": st.session_state["drhp_id"],   # set by catalogue click
    "regenerate_attempts": 0,
})
```

**Why backward-compatible:** Defaulting `drhp_id` to `DRHP_ID_DEFAULT` in `intake` means every existing Phase 1 test that invokes the graph without a `drhp_id` key keeps passing. The 219-test baseline does not break. New tests assert dynamic selection.

**Also check** `refuse_with_reformulation` node — it calls `search_relaxed(query_vector, drhp_id, limit)`. Verify it too reads `state["drhp_id"]` rather than the constant (same one-line change). `search_relaxed` already takes `drhp_id` as a parameter. ✅

### Pattern 2: Generalized Ingestion Pipeline

**What:** `pipelines/ingest_swiggy.py` becomes `pipelines/ingest.py` with a parameterized entry point. The four steps (parse → chunk → embed → upsert) are already functions; only the module-level constants (`DRHP_ID`, `PDF_PATH`, `JSON_CACHE_PATH`) are hard-coded.

**Recommended signature:**
```python
# pipelines/ingest.py
def ingest_drhp(
    drhp_id: str,                 # e.g. "hyundai_2024_10"
    pdf_path: Path,               # data/<drhp_id>/<file>.pdf
    *,
    json_cache_path: Path | None = None,   # defaults to pdf_path.with_suffix(".docling.json")
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    dry_run: bool = False,
) -> IngestReport:               # chunk count, page coverage, token stats, sha verified
    """Parse → chunk(drhp_id) → embed → upsert. Idempotent per drhp_id."""
```
- `chunk_sections(...)` already accepts `drhp_id` (it defaults to the Swiggy constant — just pass it explicitly).
- `extract_sections_from_docling`, `embed_chunks`, `upsert_chunks` are already drhp-agnostic.
- Keep a thin Typer CLI: `python -m pipelines.ingest <drhp_id> --pdf <path>` and a `ingest-all` command that loops over `data/catalogue.json`.
- Preserve `ingest_swiggy.py` as a deprecated shim (or delete + repoint tests) — planner's call; lowest-risk is to keep it importing from `ingest.py`.

**Per-IPO SHA pin + cache:** Each IPO gets `data/<drhp_id>/SHA256SUMS` and a committed `docling.json` (mirrors the existing `data/swiggy_drhp/` layout). The ingest entry point should verify the PDF SHA against the pin before parsing and refuse on mismatch (P14 version-drift defense; reuses the existing `tests/unit/test_drhp_integrity.py` pattern).

**Idempotency:** Upsert uses `chunk_id` UUIDs generated fresh each run, so re-ingesting an IPO **appends duplicate points** unless cleared. Add a `delete by drhp_id filter` step before upsert, OR make chunk_ids deterministic (hash of `drhp_id + section + span`). **Recommendation: delete-by-filter then upsert** — simplest, and Qdrant supports `delete(filter=drhp_id)`. Flag this for the planner; it's a real correctness gotcha when re-ingesting.

### Pattern 3: Snapshot Pre-Computation as Canned-Query Agent Invocations

**What:** Each of the 6 snapshot blocks is a fixed query string run through the *existing* graph with the IPO's `drhp_id`. The output `GroundedAnswer` is serialized to the snapshot cache. **No new prompt, no new LLM path** (D2-04).

```python
# pipelines/snapshot_queries.py — the 6 canned queries (versioned, like prompts)
SNAPSHOT_QUERIES: dict[str, str] = {
    "metadata":         "What are the issue details: price band, lot size, issue dates, total issue size, the split between fresh issue and offer for sale, and the book running lead managers?",
    "business":         "Summarize the company's business model and what it does, in plain English.",
    "financials":       "What are the restated revenue, profit/loss, EBITDA margin, total debt, ROE and ROCE for the last three to five fiscal years?",
    "risks":            "What are the most significant company-specific risk factors disclosed?",
    "use_of_proceeds":  "What are the objects of the issue — how will the fresh-issue proceeds be used, and what portion of the offer is an offer for sale versus fresh issue?",
    "promoter":         "Who are the promoters, what are their pre-issue and post-issue shareholdings, is any promoter shareholding pledged, and are there material prior legal or regulatory matters involving the promoters?",
}

# pipelines/precompute_snapshot.py
def precompute(drhp_id: str) -> None:
    record = {"drhp_id": drhp_id, "computed_at": ..., "fields": {}}
    for field, query in SNAPSHOT_QUERIES.items():
        state = GRAPH.invoke({"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0})
        ga = state.get("grounded_answer")
        if ga is not None:
            record["fields"][field] = ga.model_dump()          # GroundedAnswer → JSON
        else:                                                   # honest "not disclosed"
            record["fields"][field] = {"refusal": (state.get("refusal") or _default_refusal(field)).model_dump()}
    Path(f"data/snapshots/{drhp_id}.json").write_text(json.dumps(record, indent=2))
```

**Cache record shape (per field) = serialized `GroundedAnswer`** — `{answer_prose, claims:[{claim_id, text, drhp_page, section, verbatim_span, span_offsets, sources:[...]}], sub_question_addressed, sub_question_unaddressed}`. Because `claim_id`s are already in the record, the snapshot page renders citation chips with the **exact same `ui/` renderer** the Q&A answers use — zero new citation code.

**Honest "DRHP doesn't disclose this":** When the agent refuses a field (e.g., a company with no pledging disclosure), store the `RefusalResponse` instead of a `GroundedAnswer`. The snapshot page renders "This DRHP does not disclose {field}" — this is the honesty-first invariant carried into the snapshot surface (parallels RAG-03). **Critical for SNAP-07** where some IPOs genuinely lack pledging/prior-matters disclosure.

### Storage Choice: JSON-per-IPO (RECOMMENDED) over SQLite

| Dimension | JSON-per-IPO (`data/snapshots/<id>.json`) | SQLite |
|-----------|-------------------------------------------|--------|
| Fits existing pattern | ✅ mirrors committed `docling.json` | ✗ new artifact type |
| Git diff-reviewable | ✅ snapshot copy reviewable in PRs | ✗ binary blob |
| Query need at ~8 IPOs | none — page loads one IPO by key | overkill |
| Citation propagation | trivial — `GroundedAnswer.model_dump()` | same, but in a column |
| HF Spaces read | committed file, no daemon | committed file, needs sqlite3 (stdlib, fine) |
| Future scale (100s IPOs) | revisit then | better then |

**Recommendation: JSON-per-IPO, committed.** Rationale: Phase 2 is ~8 IPOs, page access is point-lookup-by-drhp_id, the record is literally a serialized Pydantic model, and committing it makes the LLM-generated snapshot copy reviewable in git (a compliance + honesty asset — you can eyeball that no banned token slipped through). SQLite buys query power Phase 2 doesn't need. Revisit at Phase 4+ if the dataset grows. This is **Claude's-discretion D2** — the planner may pick SQLite, but JSON is the lower-friction call.

### Anti-Patterns to Avoid
- **Re-designing the agent for snapshots.** D2-04 is explicit: reuse the existing retrieve→generate→cite_check path. A snapshot block is just a canned query. Do not add a "snapshot mode" to the graph.
- **Computing snapshots at page-view time.** D2-03: pre-compute offline. HF Spaces cold-start + 6 LLM calls per view = dead demo (P19).
- **Re-ingesting without clearing old points.** Duplicate chunk_ids inflate the index and skew retrieval. Delete-by-drhp_id-filter before upsert.
- **A second collection per IPO.** One `drhp_chunks` collection with a `drhp_id` payload filter is the design (verified in `storage/vector.py`). Do not shard by IPO.
- **New citation renderer for snapshot blocks.** Reuse `ui/` chip + expander. The record is a `GroundedAnswer`; the renderer already handles it.
- **Letting one un-parseable DRHP block the whole catalogue (P14).** Ingest is per-IPO and failure-isolated; a failed IPO is simply absent from `catalogue.json`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-IPO retrieval filter | Custom per-IPO collections / manual filtering | `storage.vector.search(drhp_id=...)` | **Already exists**, payload-indexed, verified |
| Snapshot citation rendering | New chip/citation code | Existing `ui/` renderer over `GroundedAnswer` | Snapshot record IS a GroundedAnswer |
| Snapshot extraction LLM path | New prompt + Instructor call | Existing `generate` node via `GRAPH.invoke` | D2-04 locks reuse; cite-check + scrubber come free |
| Snapshot serialization | Hand-written dict packing | `GroundedAnswer.model_dump()` / `model_validate()` | Pydantic round-trips losslessly |
| DRHP integrity check | New SHA logic | Existing `test_drhp_integrity.py` pattern + SHA256SUMS | Already the Phase 1 convention |
| Snapshot "not disclosed" handling | Custom empty-field logic | Existing `RefusalResponse` (RAG-03 path) | Honest refusal already implemented |
| Catalogue routing | Custom router | Streamlit multipage `pages/` + query param | `pages/01_methodology.py` precedent |

**Key insight:** Phase 2's correct instinct is *"what can I NOT write?"* Almost everything is reuse. The only genuinely new code is: the `drhp_id` thread (≈6 one-line edits), the ingest parameterization, the 6 canned queries, the snapshot pre-compute loop, the snapshot cache reader, and two Streamlit pages (UI-SPEC-driven).

## Runtime State Inventory

> Phase 2 is partly a generalization/rename of `ingest_swiggy.py` → `ingest.py`, so a runtime-state audit applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Qdrant `drhp_chunks` collection currently holds (or will hold) only `swiggy_2024_11` points. New drhp_ids are *added*, not migrated — no rename of existing data. **BUT:** if Swiggy was ingested with the PyMuPDF fallback (per `INGEST_LATER.md`), re-ingesting with real Docling on Python 3.11 will create new chunk_ids → must delete old Swiggy points first (see Pattern 2 idempotency). | Data: delete-by-filter `drhp_id=swiggy_2024_11` before re-ingest; then upsert. Per-IPO ingest is additive. |
| Live service config | Qdrant Cloud collection config (HNSW, payload index on `drhp_id`) is created by `ensure_collection()` and lives in the cloud cluster, not git. Already correct for multi-IPO. No change. | None — verified `ensure_collection` already indexes `drhp_id`. |
| OS-registered state | None — no Task Scheduler / cron / launchd entries embed `swiggy` or `drhp_id`. The cron pinger (`cron_pinger.yml`) hits `/` generically. | None — verified by inspecting `.github/workflows` references in PHASE-CLOSE. |
| Secrets/env vars | `QDRANT_URL`, `QDRANT_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `LANGFUSE_*` — none reference an IPO by name. `DRHP_ID_DEFAULT` is a code constant, not an env var. | None — drhp_id is data/state, not a secret. |
| Build artifacts | `data/swiggy_drhp/swiggy_prospectus_2024_11.docling.json` is committed. If `ingest_swiggy.py` is renamed/deleted, any test importing it (`tests/integration/test_qdrant_ingest.py`, others) breaks. | Code: grep for `ingest_swiggy` imports; repoint to `pipelines.ingest` or keep a shim. |

**The canonical question — after every file is updated, what still references the old single-IPO assumption?** Answer: (1) Qdrant may hold stale single-parser Swiggy points; (2) any test/module importing `pipelines.ingest_swiggy` by name; (3) `DRHP_ID_DEFAULT` consumers (retrieve, refuse_with_reformulation) — all enumerated above. Nothing in OS/secrets layer.

## Common Pitfalls

### Pitfall P14 (OWNED): Brittle Multi-DRHP Ingestion

**What goes wrong:** 8 DRHPs from different merchant bankers have heterogeneous layouts. Docling's section detection (which keys off `section_header`/`title` labels and an ALL-CAPS heuristic in `extract_sections_from_docling`) will produce clean sections on some and a flat "Full Document" fallback on others. One IPO's financial tables parse as garbage; the whole batch stalls if not failure-isolated.

**Why it happens:** No EDGAR-equivalent standard; Indian DRHPs vary in cover-page layout, pagination scheme (Roman → Arabic offset differs per issuer — the hard-coded `ROMAN_NUMERAL_THRESHOLD_PAGE=20` is Swiggy-tuned and will be wrong for others), and table formatting.

**How to avoid (actionable):**
1. **Per-IPO failure isolation.** `ingest_drhp` is called once per IPO in a loop that catches exceptions; a failed IPO logs + is skipped + omitted from `catalogue.json`. The catalogue never lists an IPO whose snapshot couldn't be built. One bad DRHP ≠ broken product (P14 manual-fallback-queue principle).
2. **Per-IPO parse-quality gate.** After parsing, assert: section count > N (e.g. >10), at least one section name matches a known DRHP section regex ("Risk Factors", "Objects of the Issue", "Our Business", "Restated"), and page coverage spans most of the PDF. If the doc fell into the single "Full Document" fallback section, flag it `extraction_quality: "fallback"` and either route flagged financial pages through pdfplumber (CLAUDE.md's documented fallback) or down-rank that IPO.
3. **Fix the pagination heuristic.** `_infer_printed_label` hard-codes a 20-page Roman threshold. Make it per-IPO (detect the first Arabic "1" page, or accept a `front_matter_pages` override in `catalogue.json` per IPO). Otherwise citation page links will be wrong for non-Swiggy IPOs (P5 citation-drift regression).
4. **SHA-256 pin + version discrimination (DRHP vs RHP vs Prospectus).** Store which document version each `drhp_id` points to in `catalogue.json` (`doc_type: "DRHP" | "RHP" | "Prospectus"`). The price band differs between DRHP (no band) and RHP/Prospectus (band fixed). **For SNAP-02 metadata to have a real price band, prefer RHP or Prospectus over DRHP** — Swiggy already uses the Prospectus for exactly this reason (`SOURCE.md`). The "DRHP" naming in `drhp_id`/`catalogue.json` is a label; the actual file may be the RHP/Prospectus. Record both.
5. **Multi-source redundancy.** SEBI is primary (all 8 confirmed below). If a SEBI PDF link 404s later, the SHA-pinned committed mirror in `data/<drhp_id>/` is the fallback — never re-fetch at runtime.

**Warning signs:** An IPO's snapshot blocks are all refusals; a citation page link opens the wrong page; ingest produces 1 giant chunk instead of hundreds; section names are all "Full Document" / "Page N".

### Pitfall P13 (OWNED): Embedding Mismatch on Indian-English

**What goes wrong:** bge-m3 is multilingual but Indian financial English (lakh, crore, promoter group, RPT, QIB, NII, RII, HUF, KMP, bonafide) may retrieve weakly — snapshot queries like "use of proceeds" may miss the "Objects of the Issue" section; "promoter pledging" may miss cross-referenced annexures.

**Verified Phase-1 baseline (read from code):**
- `storage/vector.py::search` is **dense-only** (single bge-m3 vector, `query_points`). **There is NO BM25/hybrid retrieval in Phase 1.** ✅ confirmed.
- There **is** a reranker step (`rerank` node + bge-reranker-v2-m3) — so retrieval is dense → rerank, not hybrid.
- `01-RESEARCH.md` explicitly deferred hybrid: *"start dense-only, add hybrid in Phase 2 if recall < 0.85."* Phase 2 is where this decision lands per ROADMAP ("hybrid retrieval BM25+dense+rerank upgrades land here").

**How to avoid — measure first, then choose (do NOT build speculatively):**
1. **Section-targeted retrieval (cheapest, do this regardless).** Snapshot queries should bias toward the right DRHP section. Because chunks carry a `section` payload field, the snapshot pre-compute can optionally filter or boost by expected section name per field (e.g., financials → sections matching "Restated"/"Financial"). This sidesteps embedding weakness entirely for the structured blocks and is the highest-leverage, lowest-cost mitigation.
2. **Query expansion with an Indian-finance synonym map (cheap).** Expand snapshot query strings + user queries: `use of proceeds → objects of the issue`, `pledging → pledge, encumbered`, `promoter family → promoter group, promoter and promoter group`. A small static dict applied at embed time. Low risk, high recall gain on the acronym-heavy queries.
3. **Hybrid BM25+dense (only if measured recall justifies).** Add a sparse leg via **Qdrant native sparse vectors** (preferred — no second index, already supported v1.10+) or `rank_bm25`, fused with RRF before the existing reranker. **Gate this on a measured recall@10 number** from a small Indian-finance query set across 2-3 IPOs. If section-targeting + synonym expansion already clear the bar, skip the hybrid build. **Recommendation: build the 10-query Indian-finance recall probe in an early wave; only schedule the hybrid wave if it fails.**

**Why measure-first:** P13 is HIGH severity but the mitigation cost varies 10x (synonym dict = an hour; full hybrid + RRF + re-eval = a wave). The honest engineering call is to instrument recall, then spend. Building hybrid speculatively risks scope creep (P20) on a breadth phase.

### Pitfall P2 carry-over: Hallucinated Numbers in Financials Snapshot (SNAP-04)

**What:** The financials block (revenue/profit/margins/debt/ROE/ROCE over 3-5 years) is the single highest hallucination-risk snapshot field — DRHPs show H1FYxx + FY23 + FY22 + FY21 columns side-by-side; the LLM can grab the wrong column. The existing cite-check has a number-set check (`claim_numbers.issubset(window_numbers)` per `01-RESEARCH.md` Pattern 3) that catches fabricated numbers, so the existing pipeline already gates this. **But** snapshot financials are pre-computed once and committed — a wrong-but-grounded number (right number, wrong fiscal year) passes cite-check. **Mitigation:** the financials snapshot is the one block to spot-check by hand per IPO before committing the snapshot JSON (it's reviewable precisely because it's committed JSON — another argument for the JSON store). Phase 3 adds the numeric-faithfulness ≥0.95 gate; Phase 2 relies on cite-check + committed-JSON human review.

## Code Examples

### Catalogue loader + drhp_id selection (runtime)
```python
# Source: derived from existing app.py session-state pattern + storage/vector.py contract
import json, streamlit as st
from pathlib import Path

@st.cache_data
def load_catalogue() -> list[dict]:
    return json.loads(Path("data/catalogue.json").read_text())["ipos"]

@st.cache_data
def load_snapshot(drhp_id: str) -> dict:
    return json.loads(Path(f"data/snapshots/{drhp_id}.json").read_text())

# catalogue page: clicking a card sets the active IPO
st.session_state["drhp_id"] = selected["drhp_id"]   # then st.switch_page("pages/snapshot.py")
```

### Snapshot block render reuses the existing GroundedAnswer renderer
```python
# Source: reuses ui/ citation renderer over a deserialized GroundedAnswer
from agent.schemas import GroundedAnswer, RefusalResponse

field = load_snapshot(drhp_id)["fields"]["financials"]
if "refusal" in field:
    render_refusal(RefusalResponse.model_validate(field["refusal"]))   # honest "not disclosed"
else:
    ga = GroundedAnswer.model_validate(field)
    render_grounded_answer(ga)   # SAME renderer as Q&A — chips + expanders for free
```

## State of the Art

| Old (Phase 1) | New (Phase 2) | Why |
|---------------|---------------|-----|
| `DRHP_ID_DEFAULT` hard-coded in retrieve | `drhp_id` in GraphState, supplied by caller | Multi-IPO |
| `pipelines/ingest_swiggy.py` (constants) | `pipelines/ingest.py(drhp_id, pdf_path, ...)` | N IPOs |
| Single `data/swiggy_drhp/` | `data/<drhp_id>/` per IPO + `data/catalogue.json` | Catalogue |
| Q&A only | Q&A + 6 pre-computed cited snapshot blocks | Snapshot surface |
| Dense-only retrieval | Dense + section-targeting + synonym expansion (hybrid only if recall fails) | P13 |
| PyMuPDF fallback (Python 3.13) | Real Docling (Python 3.11 now available) | Better tables |

**Deprecated/outdated:** The `INGEST_LATER.md` note (Qdrant upsert + Docling deferred on Python 3.13) is resolved by Python 3.11 — Phase 2 should complete the real Docling ingest that Phase 1 deferred.

## DRHP Source List (D2-01 verification — all confirmed on SEBI)

All 8 candidate IPOs have publicly downloadable filings on `sebi.gov.in`. For SNAP-02 (price band, lot size), **prefer the RHP or Prospectus over the DRHP** (DRHP has no fixed price band). `drhp_id` is a label; record the actual `doc_type` used.

| IPO | drhp_id (suggested) | Outcome framing | Best SEBI source (confirmed) | doc_type to use | Notes |
|-----|---------------------|-----------------|------------------------------|-----------------|-------|
| Swiggy | `swiggy_2024_11` | mixed/disappointment | [Prospectus Nov-2024](https://www.sebi.gov.in/filings/public-issues/nov-2024/swiggy-limited-prospectus_88320.html) | Prospectus (done) | Already ingested (PyMuPDF fallback — re-ingest w/ Docling) |
| Hyundai Motor India | `hyundai_2024_10` | winner (largest Indian IPO) | [DRHP Jun-2024](https://www.sebi.gov.in/filings/public-issues/jun-2024/hyundai-motor-india-limited-drhp_84186.html) · [RHP Oct-2024](https://www.sebi.gov.in/filings/public-issues/oct-2024/hyundai-motor-india-limited-rhp_87531.html) · [Prospectus Oct-2024](https://www.sebi.gov.in/filings/public-issues/oct-2024/hyundai-motor-india-limited-prospectus_87741.html) | RHP or Prospectus | Walking-skeleton IPO #2 |
| Ola Electric | `ola_electric_2024_08` | disappointment | [DRHP Dec-2023](https://www.sebi.gov.in/filings/public-issues/dec-2023/ola-electric-mobility-limited-drhp_80215.html) · [RHP Jul-2024](https://www.sebi.gov.in/filings/public-issues/jul-2024/ola-electric-mobility-limited-rhp_86238.html) · [Prospectus Aug-2024](https://www.sebi.gov.in/filings/public-issues/aug-2024/ola-electric-mobility-limited-prospectus_86239.html) | RHP or Prospectus | EV; large risk section |
| Zomato | `zomato_2021_07` | winner | [DRHP Apr-2021](https://www.sebi.gov.in/filings/public-issues/apr-2021/zomato-limited-drhp_49956.html) | DRHP (find RHP for band) | First new-age tech IPO |
| Nykaa (FSN E-Commerce) | `nykaa_2021_10` | winner-then-faded | [DRHP Aug-2021](https://www.sebi.gov.in/filings/public-issues/aug-2021/fsn-e-commerce-ventures-limited_51574.html) | DRHP (find RHP for band) | Profitable new-age outlier |
| Paytm (One97) | `paytm_2021_11` | disappointment (iconic) | DRHP Jul-2021 — landing page on SEBI public-issues archive; direct PDF observed at `sebi_data/attachdocs/jul-2021/1626426805246.pdf` | DRHP/RHP | Confirm exact landing URL at ingest time |
| LIC | `lic_2022_05` | disappointment | [DRHP Feb-2022](https://www.sebi.gov.in/filings/public-issues/feb-2022/life-insurance-corporation-of-india_56035.html) · [Corrigendum Feb-2022](https://www.sebi.gov.in/filings/public-issues/feb-2022/life-insurance-corporation-of-india-corrigendum-to-drhp_56090.html) | DRHP + corrigendum (find RHP for band) | **Largest DRHP — may stress Docling/Qdrant 1GB free tier; check index-size estimate** |
| Mamaearth (Honasa) | `honasa_2023_11` | mixed | [DRHP Dec-2022](https://www.sebi.gov.in/filings/public-issues/dec-2022/honasa-consumer-limited-drhp_66770.html) · [RHP Oct-2023](https://www.sebi.gov.in/filings/public-issues/oct-2023/honasa-consumer-limited-rhp_78310.html) · [Prospectus Nov-2023](https://www.sebi.gov.in/filings/public-issues/nov-2023/honasa-consumer-limited-prospectus_78722.html) | RHP or Prospectus | D2C |

**SME flag:** All 8 are NSE/BSE **mainboard** IPOs — none are SME. No substitution needed; D2-01's "substitute if unavailable" clause is not triggered.

**Qdrant free-tier capacity (P19/cost):** Phase 1's `_print_index_size_estimate` warns at >50% of the 1GB free tier for one DRHP. **8 DRHPs (LIC especially) may exceed 1GB.** The planner MUST run the dry-run size estimate across all 8 and, if needed, (a) use the paid-but-free-tier-generous self-host Qdrant on Fly.io, or (b) reduce chunk overlap / drop low-value sections. Flag as an Open Question.

**"Currently-open" IPO (OPS-01 "+1-2 currently-open"):** All 8 above are *closed/listed* IPOs. OPS-01 also asks for 1-2 currently-open. As of June 2026 the open-IPO set is time-varying — recommend the planner treat "currently-open" as a single hand-curated late-add at execution time (whatever mainboard IPO is open that week, ingested via the same `ingest_drhp` path), or descope to "recent" with a note, since a portfolio demo doesn't need live freshness. **Open Question — planner decides.**

## Section Conventions (Indian DRHP) — per-field retrieval targets (§5)

| Snapshot field (SNAP) | Primary DRHP sections to retrieve | Indian-DRHP section names | Honest-gap handling |
|-----------------------|-----------------------------------|---------------------------|---------------------|
| Metadata (SNAP-02) | Cover page; "The Issue"; "General Information"; "Capital Structure" | Price band & lot size on cover (RHP/Prospectus only); BRLMs in "General Information" | DRHP-only file → no price band → render "Price band set at RHP stage" |
| Business (SNAP-03) | "Our Business"; "Industry Overview"; MD&A | "OUR BUSINESS", "INDUSTRY OVERVIEW", "MANAGEMENT'S DISCUSSION AND ANALYSIS" | n/a — always present |
| Financials (SNAP-04) | "Restated Financial Statements"; "Financial Information"; "Other Financial Information" (ratios) | "RESTATED ... FINANCIAL STATEMENTS"; ratios in "Other Financial Information"/"Basis for Offer Price" | ROE/ROCE sometimes only in "Basis for Offer Price"; if absent, refuse that metric |
| Risks (SNAP-05) | "Risk Factors" | "RISK FACTORS" (internal: "Internal" vs "External"/"Industry") | Boilerplate filtering is Phase 3 (IDF); Phase 2 surfaces top company-specific risks via the query phrasing |
| Use of proceeds (SNAP-06) | "Objects of the Issue"; "The Issue" (OFS vs fresh split) | "OBJECTS OF THE OFFER"/"OBJECTS OF THE ISSUE" | OFS-only issues (e.g. LIC mostly OFS) → foreground "100% OFS — no fresh capital raised" (D2-06 is the signal) |
| Promoter (SNAP-07) | "Our Promoters and Promoter Group"; "Capital Structure" (pre/post holdings, pledge); "Outstanding Litigation" | "OUR PROMOTERS", "CAPITAL STRUCTURE", "OUTSTANDING LITIGATION AND MATERIAL DEVELOPMENTS" | Pledging often not disclosed → refuse that sub-field honestly |

## Validation Architecture

> `workflow.nyquist_validation` not set to false → section REQUIRED. Phase 1 established 219 unit tests + pytest + integration fixtures.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest; established Phase 1) |
| Config file | `pyproject.toml` (Phase 1) / existing `tests/conftest.py` |
| Quick run command | `pytest tests/unit -x -q` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| (gen) | `drhp_id` threads through graph; retrieve filters on it | unit | `pytest tests/unit/test_drhp_id_threading.py -x` | ❌ Wave 0 |
| (gen) | `intake` defaults missing `drhp_id` to DEFAULT (back-compat) | unit | `pytest tests/unit/test_intake_drhp_default.py -x` | ❌ Wave 0 |
| SNAP-01 | catalogue.json loads + schema-validates; cards list | unit | `pytest tests/unit/test_catalogue_loader.py -x` | ❌ Wave 0 |
| SNAP-02..07 | snapshot cache read/write round-trips GroundedAnswer + Refusal | unit | `pytest tests/unit/test_snapshot_cache.py -x` | ❌ Wave 0 |
| (ingest) | `ingest_drhp(drhp_id, pdf)` produces drhp-tagged chunks; SHA gate | unit | `pytest tests/unit/test_ingest_generalized.py -x` | ❌ Wave 0 |
| (ingest) | re-ingest deletes old points (no duplicates) | unit | `pytest tests/unit/test_ingest_idempotent.py -x` | ❌ Wave 0 |
| (ingest) | parse-quality gate flags fallback/garbage parse (P14) | unit | `pytest tests/unit/test_parse_quality_gate.py -x` | ❌ Wave 0 |
| SNAP-01/02 | ingest a 2nd IPO (Hyundai) end-to-end → searchable by drhp_id | integration | `pytest tests/integration/test_second_ipo_ingest.py -x` | ❌ Wave 0 |
| SNAP-03..07 | precompute snapshot for 1 IPO → 6 fields, each grounded-or-refused | integration | `pytest tests/integration/test_snapshot_precompute.py -x` | ❌ Wave 0 |
| SNAP-04 | financials snapshot faithfulness on a tiny gold set | eval | `pytest tests/eval/test_snapshot_financials_faithfulness.py` | ❌ Wave 0 |
| P13 | Indian-finance recall probe (10 queries × 2-3 IPOs) | eval | `pytest tests/eval/test_indian_finance_recall.py` | ❌ Wave 0 (gates hybrid decision) |

### Sampling Rate
- **Per task commit:** `pytest tests/unit -x -q` (must stay green; 219 baseline + new)
- **Per wave merge:** `pytest -q` (full, incl. integration; integration may need Qdrant + .env)
- **Phase gate:** Full suite green; snapshot JSON for ≥2 IPOs committed + human-reviewed financials; P13 recall probe run and hybrid decision recorded.

### Wave 0 Gaps
- [ ] `tests/unit/test_drhp_id_threading.py` — covers the core generalization
- [ ] `tests/unit/test_catalogue_loader.py` + `tests/unit/test_snapshot_cache.py`
- [ ] `tests/unit/test_ingest_generalized.py` + `test_ingest_idempotent.py` + `test_parse_quality_gate.py`
- [ ] `tests/integration/test_second_ipo_ingest.py` + `test_snapshot_precompute.py`
- [ ] `tests/eval/test_snapshot_financials_faithfulness.py` — extend the 13-entry gold set with snapshot-field gold rows
- [ ] `tests/eval/test_indian_finance_recall.py` — the P13 measurement that gates the hybrid wave
- [ ] What to commit: `data/catalogue.json`, `data/<drhp_id>/docling.json` + `SHA256SUMS` + `SOURCE.md` per IPO, `data/snapshots/<drhp_id>.json`. What to `.gitignore`: the raw PDFs if large (use the SEBI URL + SHA as provenance; do NOT host/serve PDFs — Security note below); Qdrant local storage; `.env`.

## Security Domain

> `security_enforcement` not disabled → REQUIRED. Phase 2 adds minimal new surface; the Phase 1 STRIDE posture (scrubber, cite-check, masked secrets) carries forward unchanged.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in v1 (no user accounts — out of scope) |
| V3 Session Management | minimal | Streamlit session state holds `drhp_id` only (non-sensitive) |
| V4 Access Control | no | Public read-only catalogue |
| V5 Input Validation | yes | `drhp_id` from session/query-param MUST be validated against the catalogue allow-list before reaching `search(drhp_id=...)` — never pass raw user input to the Qdrant filter |
| V6 Cryptography | yes (integrity) | SHA-256 pin per DRHP (existing pattern); not secrecy, integrity |

### Known Threat Patterns for Phase 2
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `catalogue.json` tampering (malicious drhp_id / URL) | Tampering | catalogue.json is repo-committed + reviewed in PR; treated as trusted config, not user input |
| Snapshot-cache poisoning (committed JSON contains a banned token / wrong claim) | Tampering / Repudiation | Snapshot JSON is git-reviewable; run the existing `compliance/scrubber` over all snapshot `answer_prose` at pre-compute time AND assert at load time; financials human-reviewed before commit |
| More DRHPs = more prompt-injection-via-content surface | Tampering (LLM) | DRHP text is from trusted SEBI source (not user upload — E5 deferred); cite-check + scrubber already gate output; the 8 DRHPs are SHA-pinned so content can't silently change |
| `drhp_id` query-param injection into Qdrant filter | Tampering | **V5 control above** — allow-list validation against catalogue keys before `search()` |
| Hosting/serving DRHP PDFs from your domain | IP/Copyright (PITFALLS security table) | **Do NOT serve the PDFs.** Link out to the SEBI URL; the committed copy is provenance/SHA only. Citation "View on SEBI" links point to sebi.gov.in. |

**New threat-model block for the planner:** the only genuinely new untrusted-data path is `drhp_id` selection from the Streamlit query param / session — validate it against `catalogue.json` keys. Everything else (DRHP content) is trusted-source + SHA-pinned + already gated by Phase 1's scrubber/cite-check.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JSON-per-IPO snapshot store is preferable to SQLite at ~8 IPOs | §3 storage choice | Low — planner may pick SQLite (D2 discretion); both round-trip GroundedAnswer |
| A2 | 8 DRHPs may exceed Qdrant 1GB free tier (esp. LIC) | DRHP source list | Medium — if true, needs self-host Qdrant or chunk reduction; MUST run dry-run estimate |
| A3 | Paytm exact SEBI landing-page URL needs confirmation at ingest (direct PDF observed, landing not opened) | DRHP source list | Low — direct PDF path observed; verify landing at ingest |
| A4 | Section-targeting + synonym expansion will clear P13 recall bar without full hybrid | §6 P13 | Medium — if recall still fails, schedule the hybrid wave (rank_bm25 / Qdrant sparse) |
| A5 | `ROMAN_NUMERAL_THRESHOLD_PAGE=20` is Swiggy-specific and wrong for others | P14 | Medium — wrong page links (P5 regression) if not made per-IPO |
| A6 | Re-ingest appends duplicate points unless delete-by-filter is added | Pattern 2 idempotency | Medium — index pollution + skewed retrieval if missed |
| A7 | "currently-open" IPO (OPS-01) is a late-add at execution time, not pre-research | DRHP source list | Low — descopable to "recent" with a note |
| A8 | Swiggy was ingested via PyMuPDF fallback and should be re-ingested with Docling | Runtime State Inventory | Low — verifiable by inspecting committed docling.json provenance |

**These A-items are the decisions discuss-phase/planner should confirm before locking.**

## Open Questions

1. **SQLite vs JSON snapshot store** — Recommendation: JSON-per-IPO committed (§3). Planner's call (D2 discretion).
2. **Hybrid BM25 retrieval in Phase 2 vs defer** — Recommendation: build the P13 recall probe early; only schedule the hybrid wave if section-targeting + synonyms fail to clear the bar. Do not build speculatively.
3. **Qdrant 1GB free-tier capacity across 8 DRHPs** — Run `_print_index_size_estimate` dry-run across all 8 in an early task; if >1GB, decide self-host vs chunk reduction. (A2)
4. **"Currently-open" IPO for OPS-01** — Recommendation: single hand-curated late-add via the same ingest path, or descope to "recent" with a methodology note. (A7)
5. **DRHP vs RHP vs Prospectus per IPO** — Use RHP/Prospectus where a real price band is needed for SNAP-02; record `doc_type` in catalogue.json. Confirm which version each IPO uses at ingest.
6. **Re-ingest idempotency strategy** — delete-by-drhp_id-filter (recommended) vs deterministic chunk_ids. Planner picks; must be solved before re-ingesting Swiggy with Docling.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Real Docling ingest (Phase 1 deferred on 3.13) | must verify on target | 3.11+ | PyMuPDF fallback (lower table quality) |
| Docling | Parsing 7 new DRHPs | installed Phase 1 (stack) | `>=2.95` | pdfplumber on flagged pages |
| Qdrant (Cloud or self-host) | Multi-IPO storage | needs running daemon (Phase 1 deferred upsert) | server `>=1.13` | self-host Fly.io if 1GB free tier exceeded |
| Gemini/Groq API keys | Snapshot pre-compute LLM calls | env-dependent | — | Groq fallback already in generate node |
| bge-m3 (torch) | Embedding (Phase 1 noted torch missing on 3.13) | needs torch on 3.11 | — | none — required for embed |

**Missing dependencies with no fallback:** A running Qdrant instance and bge-m3/torch are hard requirements that Phase 1 deferred (`INGEST_LATER.md`). Phase 2 cannot complete ingest without them — surface to planner as a Wave 0 setup gate.

**Missing dependencies with fallback:** Docling → pdfplumber (per-page); Qdrant Cloud free tier → self-host if over capacity.

## Sources

### Primary (HIGH confidence)
- Direct code read: `pipelines/ingest_swiggy.py`, `storage/vector.py`, `agent/schemas.py`, `agent/graph.py`, `agent/state.py`, `agent/policies.py`, `agent/nodes/retrieve.py`, `agent/nodes/intake.py`, `app.py`, `data/swiggy_drhp/SOURCE.md`, `01-PHASE-CLOSE.md` — established the exact generalization points and existing contracts
- `02-CONTEXT.md` (D2-01..D2-08), `ROADMAP.md` (Phase 2 goal + P13/P14 ownership), `REQUIREMENTS.md` (SNAP-01..07, OPS-01), `.planning/research/PITFALLS.md` (P2, P13, P14, P19), `CLAUDE.md` (stack)
- SEBI public-issues filings (all 8 IPOs confirmed via search returning `sebi.gov.in` URLs):
  - [Hyundai DRHP](https://www.sebi.gov.in/filings/public-issues/jun-2024/hyundai-motor-india-limited-drhp_84186.html) / [RHP](https://www.sebi.gov.in/filings/public-issues/oct-2024/hyundai-motor-india-limited-rhp_87531.html) / [Prospectus](https://www.sebi.gov.in/filings/public-issues/oct-2024/hyundai-motor-india-limited-prospectus_87741.html)
  - [Ola Electric DRHP](https://www.sebi.gov.in/filings/public-issues/dec-2023/ola-electric-mobility-limited-drhp_80215.html) / [RHP](https://www.sebi.gov.in/filings/public-issues/jul-2024/ola-electric-mobility-limited-rhp_86238.html) / [Prospectus](https://www.sebi.gov.in/filings/public-issues/aug-2024/ola-electric-mobility-limited-prospectus_86239.html)
  - [Zomato DRHP](https://www.sebi.gov.in/filings/public-issues/apr-2021/zomato-limited-drhp_49956.html)
  - [Nykaa (FSN) DRHP](https://www.sebi.gov.in/filings/public-issues/aug-2021/fsn-e-commerce-ventures-limited_51574.html)
  - [LIC DRHP](https://www.sebi.gov.in/filings/public-issues/feb-2022/life-insurance-corporation-of-india_56035.html) / [Corrigendum](https://www.sebi.gov.in/filings/public-issues/feb-2022/life-insurance-corporation-of-india-corrigendum-to-drhp_56090.html)
  - [Mamaearth (Honasa) DRHP](https://www.sebi.gov.in/filings/public-issues/dec-2022/honasa-consumer-limited-drhp_66770.html) / [RHP](https://www.sebi.gov.in/filings/public-issues/oct-2023/honasa-consumer-limited-rhp_78310.html) / [Prospectus](https://www.sebi.gov.in/filings/public-issues/nov-2023/honasa-consumer-limited-prospectus_78722.html)
  - Paytm DRHP Jul-2021 — SEBI public-issues archive (confirm landing URL at ingest)

### Secondary (MEDIUM confidence)
- `01-RESEARCH.md` — Phase 1 Docling/chunking recipe, cite-check Pattern 3, hybrid-deferral note ("add hybrid in Phase 2 if recall < 0.85")

## Metadata

**Confidence breakdown:**
- Ingestion generalization: HIGH — verified against actual code; storage layer already multi-IPO
- DRHP sources: HIGH — all 8 confirmed on sebi.gov.in
- Snapshot architecture: HIGH — reuses verified GroundedAnswer/Claim schema; pre-compute is canned-query invocation
- P14 mitigations: HIGH — concrete and code-anchored (failure isolation, parse-quality gate, pagination fix, SHA pin)
- P13 mitigations: MEDIUM — measure-first is the right posture, but the recall numbers that decide hybrid-vs-defer don't exist yet
- Qdrant capacity / "currently-open" handling: MEDIUM — needs an execution-time measurement / decision

**Research date:** 2026-06-23
**Valid until:** 2026-07-23 (stable; SEBI URLs are permanent for filed docs; stack is locked)
</content>
</invoke>
