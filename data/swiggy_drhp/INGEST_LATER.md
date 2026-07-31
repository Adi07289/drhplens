# Swiggy DRHP — Deferred Qdrant Upsert

> **UPDATE 2026-07-23 (Job B / EVAL-03):** The degenerate single-blob PyMuPDF
> fallback below was replaced. Docling cannot run in this env (needs torch≥2.4 +
> torchvision, which conflict with the pinned Phase-5 numpy/shap stack), so a
> torch-free **page-anchored** parser was added — `pipelines.ingest.parse_drhp_pages`
> (PyMuPDF text + pdfplumber table rows, ONE section per page). The prospectus was
> re-parsed (541 pages → **1,885 single-page-anchored chunks**), re-embedded via the
> ONNX (fastembed) path, and re-upserted to Qdrant `drhp_chunks` (old swiggy chunks
> deleted first; collection now 1,885 points). This fixed the `(0,284)` giant-span
> chunks that were poisoning cite-check windows. Numeric grounding improved
> materially (e.g. num-001 issue-size now grounds). A full gate re-measurement is
> pending — blocked by Gemini free-tier rate limits, not the fix.

The Qdrant upsert was deferred during Wave 2 because the Qdrant daemon was not
running and sentence-transformers (bge-m3) required torch, which is not installed
in the current Python 3.13 environment.

The JSON cache (`swiggy_prospectus_2024_11.docling.json`) has been committed using
a PyMuPDF fallback parser. When Docling is available, re-run `parse --force` to
replace it with the richer Docling-native output.

---

## Steps to Complete the Ingestion

```bash
# 1. Start Qdrant locally
docker run -d -p 6333:6333 -p 6334:6334 \
  -v ~/.qdrant/drhplens:/qdrant/storage \
  --name drhplens-qdrant qdrant/qdrant

# 2. Verify Qdrant is reachable
curl -sf http://localhost:6333/healthz

# 3. Configure connection (only if .env doesn't already have these)
test -f .env || touch .env
grep -q '^QDRANT_URL=' .env || echo 'QDRANT_URL=http://localhost:6333' >> .env
grep -q '^QDRANT_API_KEY=' .env || echo 'QDRANT_API_KEY=' >> .env

# 4. (Optional but recommended) Re-parse with Docling for richer structure
#    Requires: pip install docling sentence-transformers FlagEmbedding
#    Skip this step to use the PyMuPDF-based JSON cache (1,311 chunks)
python -m pipelines.ingest_swiggy parse --force

# 5. Run real ingestion (parse from cache + chunk + embed + upsert)
python -m pipelines.ingest_swiggy all

# 6. Verify ingestion succeeded
pytest tests/integration/test_qdrant_ingest.py -x
```

---

## Expected Collection State After Upsert

- **Collection name:** `drhp_chunks`
- **Embedding model:** `BAAI/bge-m3` (1024-dim, float32, cosine distance)
- **Chunks (PyMuPDF cache):** ~1,311 points
- **Chunks (Docling re-parse):** ~5,000–8,000 points (estimated)
- **Estimated collection size:** 5–30 MB (well within Qdrant 1 GB free tier)
- **Payload fields per point:** chunk_id, drhp_id, section, page_start, page_end,
  printed_page_label, chunk_text, span_offsets

Once ingested, the integration test at `tests/integration/test_qdrant_ingest.py`
will verify the collection exists, has the correct vector config, and can answer
a sample semantic query about Swiggy risk factors.
