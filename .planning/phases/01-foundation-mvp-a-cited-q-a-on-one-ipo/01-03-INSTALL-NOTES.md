# Wave 2 Install Notes — Heavy Dependencies

**Date:** 2026-05-28
**Python:** 3.13.2 (system .venv at `/Users/adityasharma/agentic-rag-app/.venv`)

---

## Installed Successfully

| Package | Version | Status |
|---------|---------|--------|
| tiktoken | 0.13.0 | OK |
| qdrant-client | 1.18.0 | OK |
| PyMuPDF | 1.27.2.3 | OK (fallback parser) |
| pdfplumber | 0.11.9 | OK (fallback parser) |
| typer | 0.26.2 | OK (already present) |
| rich | 15.0.0 | OK (already present) |

## Partially Installed (no-deps only)

| Package | Version | Status | Reason |
|---------|---------|--------|--------|
| sentence-transformers | 5.5.1 | Installed --no-deps | No torch wheel for Python 3.13 |
| transformers | 5.9.0 | Installed --no-deps | Required by sentence-transformers |
| huggingface_hub | present | Installed --no-deps | Required by transformers |

## Not Installed

| Package | Status | Reason |
|---------|--------|--------|
| torch | FAILED | No prebuilt wheel for Python 3.13 on macOS arm64 (as of 2026-05) |
| docling | FAILED | Requires torch (DoclingDocument uses torch for TableFormer) |
| FlagEmbedding | NOT ATTEMPTED | Requires torch |

---

## Impact

1. **tests/unit/test_embedder.py** — Patching approach used (`unittest.mock.patch`
   at the `tools.embedder.SentenceTransformer` attribute). All 7 tests pass because
   the real model is never loaded. The `tools/embedder.py` module was updated to
   use a try/except ImportError so `SentenceTransformer = None` when not installed,
   preserving the patchable module-level attribute.

2. **dry-run** — PyMuPDF fallback used instead of Docling. Parser extracts text and
   detects headings via bold-font heuristic. 34 sections / 1,311 chunks produced
   (Docling would yield ~150–200 sections / ~5,000–8,000 chunks with table awareness).

3. **embed step** — Skipped in dry-run (bge-m3 model requires torch). Chunker and
   ChunkPayload schema are fully exercised.

---

## Resolution Path

To get Docling + sentence-transformers working:

**Option A (recommended): Use Python 3.11 or 3.12**
```bash
# Create a new venv with Python 3.11
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install docling sentence-transformers FlagEmbedding qdrant-client tiktoken
pip install typer rich pydantic pytest
```

**Option B: Use Hugging Face Spaces (ships with torch pre-installed)**
The production environment (HF Spaces CPU 2vCPU/16GB) ships with torch and all
heavy deps. `pip install docling sentence-transformers FlagEmbedding` will succeed
there without conflict.

**Option C: Install torch nightly for Python 3.13 (experimental)**
```bash
pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cpu
pip install docling sentence-transformers FlagEmbedding
```
Note: Nightly torch may have API instability. Verify docling works before using.
