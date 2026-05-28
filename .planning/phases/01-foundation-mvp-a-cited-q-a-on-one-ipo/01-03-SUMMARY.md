---
phase: "01"
plan: "03"
subsystem: "ingestion-pipeline"
tags: ["wave-2", "drhp-ingestion", "chunker", "embedder", "docling-fallback"]
dependency_graph:
  requires: ["01-01 (scaffolding)", "01-02 (schemas + scrubber)"]
  provides: ["storage/vector.py ChunkPayload", "pipelines/ingest_swiggy.py", "tools/embedder.py", "data/swiggy_drhp JSON cache"]
  affects: ["01-04 (LangGraph agent retrieval)", "01-05 (evals)"]
tech_stack:
  added: ["tiktoken", "PyMuPDF (fallback parser)", "qdrant-client", "typer", "rich"]
  patterns: ["section-aware chunking", "storage-bus isolation (pipeline writes, agent reads)", "lazy import for mockable deps"]
key_files:
  created:
    - storage/vector.py
    - tools/embedder.py
    - tools/reranker.py
    - pipelines/ingest_swiggy.py
    - tests/unit/test_embedder.py
    - tests/unit/test_chunker.py
    - tests/unit/test_parser.py
    - tests/integration/test_qdrant_ingest.py
    - data/swiggy_drhp/swiggy_prospectus_2024_11.docling.json (PyMuPDF cache)
    - data/swiggy_drhp/INGEST_LATER.md
  modified:
    - tools/embedder.py (lazy SentenceTransformer import for CI testability)
decisions:
  - "PyMuPDF fallback parser used for dry-run (torch unavailable on Python 3.13)"
  - "SentenceTransformer import made lazy (try/except) to preserve patchability"
  - "JSON cache committed (PyMuPDF-based); Docling re-parse deferred to Python 3.11 env"
  - "Embed step deferred with Qdrant upsert; see INGEST_LATER.md"
metrics:
  duration: "~45 min (including dep installs)"
  completed: "2026-05-28"
  tasks_completed: 3
  files_created: 9
---

# Phase 01 Plan 03: DRHP Ingestion Pipeline — Wave 2 Summary

**One-liner:** PyMuPDF-fallback ingest pipeline producing 1,311 section-aware chunks from 541-page Swiggy DRHP; storage-bus contract, embedder wrapper, and 128 passing unit tests.

---

## Wave 2 Commits

| Commit | Message | Files |
|--------|---------|-------|
| `91d363d` | feat(01-03): Task 1 — storage bus contract, embedder/reranker wrappers | storage/vector.py, tools/embedder.py, tools/reranker.py |
| `8213380` | feat(01-03): Task 2 — Docling parser + section chunker + ingest pipeline | pipelines/ingest_swiggy.py, tests/unit/test_*.py, tests/integration/test_qdrant_ingest.py |
| `0a8a3e8` | feat(01-03): Task 3 — lazy ST import; flip embedder tests green | tools/embedder.py (lazy import fix) |
| *(docs commit)* | docs(01-03): Wave 2 close — dry-run report, INGEST_LATER, SUMMARY | 01-03-DRYRUN-REPORT.md, INGEST_LATER.md, 01-03-SUMMARY.md, 01-03-INSTALL-NOTES.md |

---

## File-by-File Inventory

| File | Purpose |
|------|---------|
| `storage/vector.py` | ChunkPayload dataclass + Qdrant collection helpers; EMBEDDING_DIM=1024 |
| `tools/embedder.py` | bge-m3 wrapper with lru_cache singleton; lazy import for CI |
| `tools/reranker.py` | bge-reranker-v2-m3 wrapper stub (used in Wave 3 retrieval) |
| `pipelines/ingest_swiggy.py` | Full CLI pipeline: parse → chunk → embed → upsert; --dry-run mode |
| `tests/unit/test_parser.py` | 5 parser tests (synthetic Docling JSON fixture) — all passing |
| `tests/unit/test_chunker.py` | 8 chunker contract tests — all passing |
| `tests/unit/test_embedder.py` | 7 embedder tests (mock ST) + 1 slow test — 7 passing, 1 deselected |
| `tests/integration/test_qdrant_ingest.py` | Deferred — xfail(run=False) until Qdrant daemon running |
| `data/swiggy_drhp/swiggy_prospectus_2024_11.docling.json` | PyMuPDF-based JSON cache (34 sections; replace with Docling when available) |
| `data/swiggy_drhp/INGEST_LATER.md` | Shell snippet + instructions to complete upsert after Qdrant starts |

---

## Test Status

| Suite | Count | Status |
|-------|-------|--------|
| Wave 0 scaffolding (test_schemas, test_drhp_integrity, etc.) | ~60 | Passing |
| Wave 1 schemas + scrubber (test_scrubber, test_disclaimer, etc.) | ~48 | Passing |
| Wave 2 unit: test_parser | 5 | Passing |
| Wave 2 unit: test_chunker | 8 | Passing |
| Wave 2 unit: test_embedder (not slow) | 7 | Passing |
| Wave 2 unit: test_embedder slow (bge-m3 real) | 1 | Deselected (--no-slow) |
| Wave 2+3 stubs (test_retrieve, test_gate1, test_decompose, etc.) | 5 | Skipped (ship in Wave 3/4) |
| Integration: test_qdrant_ingest | 1 | xfail(run=False) — deferred |
| **Total passing** | **128** | |

---

## Swiggy DRHP Dry-Run Results

| Metric | Value |
|--------|-------|
| PDF pages | 541 |
| Parser used | PyMuPDF 1.27.2 (Docling fallback) |
| Sections | 34 (Docling expected: ~150–200) |
| Chunks | **1,311** |
| Avg chunk | ~431 tokens / ~1,744 chars |
| Token range | min=53 / max=576 |
| Est. Qdrant size | ~5.8 MB (0.6% of 1 GB free tier) |
| Parse time | 9.9s |
| Chunk time | 2.7s |
| Embed | Deferred (torch not available on Python 3.13) |

---

## Heavy-Dep Install Status

- tiktoken, qdrant-client, PyMuPDF, pdfplumber: **fully installed**
- sentence-transformers, transformers: **installed --no-deps** (no torch)
- torch, docling, FlagEmbedding: **not installed** (no Python 3.13 wheel)
- Resolution: use Python 3.11/3.12 env or HF Spaces (see 01-03-INSTALL-NOTES.md)

---

## Shell Snippet to Complete Upsert

```bash
# After resolving torch (Python 3.11 env or HF Spaces):
docker run -d -p 6333:6333 -p 6334:6334 \
  -v ~/.qdrant/drhplens:/qdrant/storage \
  --name drhplens-qdrant qdrant/qdrant
curl -sf http://localhost:6333/healthz
python -m pipelines.ingest_swiggy all
pytest tests/integration/test_qdrant_ingest.py -x
```

Full instructions: `data/swiggy_drhp/INGEST_LATER.md`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] SentenceTransformer module-level import prevented test collection**
- **Found during:** Task 3 (test run)
- **Issue:** `tools/embedder.py` had `from sentence_transformers import SentenceTransformer` at module level. With sentence-transformers installed --no-deps (missing torch), this caused `ModuleNotFoundError: No module named 'tqdm'` even before tests could patch it.
- **Fix:** Wrapped import in try/except ImportError; SentenceTransformer=None when unavailable. Module-level attribute preserved for patch target.
- **Files modified:** tools/embedder.py
- **Commit:** 0a8a3e8

**2. [Rule 3 - Blocking] Docling not installable on Python 3.13 (no torch wheel)**
- **Found during:** Dry-run attempt
- **Issue:** `pip install docling` requires torch; no Python 3.13 wheel on PyPI as of 2026-05.
- **Fix:** Used PyMuPDF 1.27.2 fallback parser (bold-heuristic heading detection). 1,311 chunks produced from 541-page DRHP. JSON cache committed. See INSTALL-NOTES.md for resolution path.
- **Impact:** 34 sections vs expected ~150–200 from Docling. Chunk quality is reduced (no table awareness, wider page spans). Docling re-parse deferred.

---

## Known Stubs

None that block plan goal. The embed step is intentionally deferred (Qdrant not running). The PyMuPDF JSON cache is a functional placeholder — it will be replaced when Docling is available.

---

## Recommended Next Step: Wave 3 — LangGraph Agent

**Plan:** 01-04-PLAN.md
**Dependencies needed before starting:**
1. Gemini 2.5 Flash API key → `GEMINI_API_KEY` in `.env`
2. Groq API key → `GROQ_API_KEY` in `.env`
3. Qdrant running (or mock) for retrieval tests
4. (Optional) Langfuse Cloud token → `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

Wave 3 wires the LangGraph agent graph: decompose → retrieve → rerank → synthesize → cite-check → surface disclaimer. The storage-bus and ChunkPayload contract from Wave 2 are the retrieval contract that Wave 3 consumes.
