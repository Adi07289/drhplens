# Swiggy DRHP — Deferred Qdrant Upsert

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
