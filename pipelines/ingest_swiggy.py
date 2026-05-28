"""
Swiggy DRHP Ingestion Pipeline — Wave 2 implementation.

This module is the offline build-time ingestion script for the Swiggy Nov 2024 Prospectus.
Wave 0 ships this as an importable stub so Wave 0's collection checks pass.
Wave 2 fills in the full implementation:
  1. Docling 2.95 → structured JSON (sections, tables, page anchors)
  2. Section-aware chunker (512-1024 tokens, 100-200 overlap)
  3. bge-m3 batch encode (CPU; batch=4)
  4. Qdrant Cloud upsert (collection: drhp_chunks, payload: drhp_id/section/page_start/page_end/span_offsets)

Per SKELETON.md §A (Storage Bus invariant):
- This pipeline ONLY writes to Qdrant Cloud.
- The runtime agent (agent/*) ONLY reads from Qdrant.
- They never share Python state and never invoke each other.

Usage (Wave 2+):
    python -m pipelines.ingest_swiggy
    # OR
    python pipelines/ingest_swiggy.py
"""
from __future__ import annotations


def main() -> None:
    print("Wave 2 owns this implementation.")
    print("See pipelines/ingest_swiggy.py docstring for the planned ingestion steps.")


if __name__ == "__main__":
    main()
