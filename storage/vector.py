"""
storage/vector.py — Qdrant client wrapper + ChunkPayload schema.

Storage-bus invariant (SKELETON §A / ARCHITECTURE Pattern 5):
- Batch pipelines (pipelines/ingest_swiggy.py) call upsert_chunks() — WRITES only.
- Runtime agent (agent/nodes/retrieve.py) calls search() — READS only.
- Neither side imports from the other.

ChunkPayload field names are the canonical cross-phase contract.
They MUST stay aligned with agent/schemas.RetrievedChunkRef field names
(verified by tests/unit/test_embedder.py::test_chunk_payload_field_names_match_retrieved_chunk_ref).

STRIDE T-1-04 mitigation: QDRANT_API_KEY is read from env and NEVER logged.
Errors use ***-masking on the API key value.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# ---------------------------------------------------------------------------
# Constants — single source of truth
# ---------------------------------------------------------------------------

COLLECTION_NAME: str = "drhp_chunks"
EMBEDDING_DIM: int = 1024  # bge-m3 output dimension

# ---------------------------------------------------------------------------
# ChunkPayload — the payload schema written by the pipeline and read by Wave 3.
# Field names MUST mirror agent/schemas.RetrievedChunkRef (PITFALL 4 + contract).
# ---------------------------------------------------------------------------


@dataclass
class ChunkPayload:
    """Payload stored in Qdrant for every DRHP chunk.

    Field alignment contract (from agent/schemas.py):
      chunk_id, page_start, page_end, section, span_offsets — exact names.

    Extra fields not in RetrievedChunkRef (needed by Wave 3 retrieve + cite-check):
      drhp_id, printed_page_label, chunk_text.
    """

    chunk_id: str               # UUID — Qdrant point ID + payload field
    drhp_id: str                # e.g. "swiggy_2024_11"
    section: str                # DRHP section name (e.g. "Risk Factors")
    page_start: int             # PDF page index, 0-indexed (PITFALL 4 mitigation: PDF index)
    page_end: int               # PDF page index, 0-indexed
    printed_page_label: str     # Human-readable label e.g. "iii" or "142" (PITFALL 4: visible page)
    chunk_text: str             # The verbatim chunk content
    span_offsets: tuple[int, int]  # (start_char, end_char) within chunk_text; (0, len) by default


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: QdrantClient | None = None


def client() -> QdrantClient:
    """Return a singleton QdrantClient.

    Reads QDRANT_URL and QDRANT_API_KEY from environment.
    Defaults to http://localhost:6333 with empty API key for local dev.

    STRIDE T-1-04: API key is never echoed in logs or error messages.
    """
    global _client
    if _client is None:
        url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        api_key = os.environ.get("QDRANT_API_KEY", "")
        try:
            _client = QdrantClient(url=url, api_key=api_key if api_key else None)
        except Exception as exc:
            # Mask the API key in the error message (STRIDE T-1-04)
            masked = f"{url} (api_key=***)"
            raise RuntimeError(
                f"Failed to connect to Qdrant at {masked}: {exc}"
            ) from exc
    return _client


def reset_client() -> None:
    """Reset the singleton client (useful in tests)."""
    global _client
    _client = None


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------


def ensure_collection(recreate: bool = False) -> None:
    """Create (or recreate) the Qdrant collection with HNSW config.

    Idempotent: if the collection exists and recreate=False, does nothing.
    Adds a payload index on drhp_id for fast filtered search.

    Args:
        recreate: If True, drops and re-creates the collection (use with caution
                  — destroys existing data).
    """
    c = client()

    if recreate:
        try:
            c.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # Collection may not exist yet

    # Check if collection already exists
    existing = {col.name for col in c.get_collections().collections}
    if COLLECTION_NAME in existing and not recreate:
        return

    c.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=rest.VectorParams(
            size=EMBEDDING_DIM,
            distance=rest.Distance.COSINE,
        ),
        hnsw_config=rest.HnswConfigDiff(
            m=16,
            ef_construct=200,
            full_scan_threshold=10_000,
        ),
        optimizers_config=rest.OptimizersConfigDiff(
            indexing_threshold=10_000,
        ),
    )

    # Payload index on drhp_id for filtered ANN search performance
    c.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="drhp_id",
        field_schema=rest.PayloadSchemaType.KEYWORD,
    )


# ---------------------------------------------------------------------------
# Write path (pipelines only)
# ---------------------------------------------------------------------------


def upsert_chunks(payloads: list[ChunkPayload], vectors: list[list[float]]) -> None:
    """Upsert chunk payloads + vectors into the collection.

    Creates the collection if it doesn't exist (via ensure_collection).
    Point IDs are the chunk_id strings.

    Args:
        payloads: list of ChunkPayload dataclasses
        vectors: list of 1024-float embedding vectors, parallel to payloads
    """
    if len(payloads) != len(vectors):
        raise ValueError(
            f"payloads ({len(payloads)}) and vectors ({len(vectors)}) must have the same length"
        )

    ensure_collection()
    c = client()

    points = [
        rest.PointStruct(
            id=payload.chunk_id,
            vector=vector,
            payload=asdict(payload),
        )
        for payload, vector in zip(payloads, vectors, strict=True)
    ]

    # Batch upsert in groups of 100 to avoid large single requests
    batch_size = 100
    for i in range(0, len(points), batch_size):
        c.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i : i + batch_size],
        )


# ---------------------------------------------------------------------------
# Read path (runtime agent only)
# ---------------------------------------------------------------------------


def search(
    query_vector: list[float],
    drhp_id: str,
    limit: int = 50,
) -> list[dict]:
    """Dense ANN search filtered by drhp_id.

    Returns raw Qdrant ScoredPoint dicts for Wave 3 consumption.
    score_threshold=0.3 applied to avoid returning completely irrelevant chunks.

    Uses query_points() API (qdrant-client >= 1.7; replaces deprecated search()).

    Args:
        query_vector: 1024-float bge-m3 query embedding
        drhp_id: Filter to chunks from this specific DRHP (e.g. "swiggy_2024_11")
        limit: Max results to return (default 50 for reranker input)
    """
    response = client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=rest.Filter(
            must=[
                rest.FieldCondition(
                    key="drhp_id",
                    match=rest.MatchValue(value=drhp_id),
                )
            ]
        ),
        limit=limit,
        with_payload=True,
        score_threshold=0.3,
    )
    return [
        {
            "id": str(r.id),
            "score": r.score,
            "payload": r.payload,
        }
        for r in response.points
    ]


def search_relaxed(
    query_vector: list[float],
    drhp_id: str,
    limit: int = 20,
) -> list[dict]:
    """Relaxed ANN search with no score threshold.

    Used by the refuse_with_reformulation node in Wave 3 to surface top section names
    as reformulation suggestions even when the query confidence is low.

    Per RESEARCH Open Question 5: no score_threshold, smaller limit.

    Uses query_points() API (qdrant-client >= 1.7; replaces deprecated search()).

    Args:
        query_vector: 1024-float bge-m3 query embedding
        drhp_id: Filter to chunks from this DRHP
        limit: Max results (default 20; smaller than strict search)
    """
    response = client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=rest.Filter(
            must=[
                rest.FieldCondition(
                    key="drhp_id",
                    match=rest.MatchValue(value=drhp_id),
                )
            ]
        ),
        limit=limit,
        with_payload=True,
        # No score_threshold — intentional for reformulation suggestions
    )
    return [
        {
            "id": str(r.id),
            "score": r.score,
            "payload": r.payload,
        }
        for r in response.points
    ]
