"""
pipelines/verify_index.py — Post-ingest sanity check for the Qdrant collection.

Verifies:
1. Chunk count is between 1500 and 2500 (per RESEARCH A4 sizing target)
2. Sample 5 random payloads have the full ChunkPayload field set
3. All sampled payloads have page_start <= page_end
4. All sampled payloads have span_offsets[0] <= span_offsets[1]
5. printed_page_label is non-empty in all samples
6. Index size estimate vs 1GB Qdrant free tier (warn if > 50% utilized)

Exit codes:
  0 — all checks pass
  1 — one or more checks fail

Usage:
    python -m pipelines.verify_index
    python -m pipelines.verify_index --collection drhp_chunks
"""
from __future__ import annotations

import sys
from dataclasses import fields

import typer

from storage.vector import COLLECTION_NAME, ChunkPayload, client

app = typer.Typer(help="Verify DRHPLens Qdrant index integrity.")

REQUIRED_FIELDS = {f.name for f in fields(ChunkPayload)}
MIN_CHUNK_COUNT = 1500
MAX_CHUNK_COUNT = 2500
WARN_UTILIZATION_PCT = 50
QDRANT_FREE_TIER_MB = 1024  # 1 GB free tier


@app.command()
def verify(
    collection: str = typer.Option(COLLECTION_NAME, "--collection", help="Qdrant collection name"),
    min_chunks: int = typer.Option(MIN_CHUNK_COUNT, "--min-chunks"),
    max_chunks: int = typer.Option(MAX_CHUNK_COUNT, "--max-chunks"),
) -> None:
    """Run all verification checks and report results. Exit 0 on pass, 1 on fail."""
    c = client()
    failures: list[str] = []

    print(f"Verifying Qdrant collection: {collection}")
    print("-" * 50)

    # Check 1: Collection exists
    existing = {col.name for col in c.get_collections().collections}
    if collection not in existing:
        print(f"FAIL: Collection '{collection}' does not exist.")
        sys.exit(1)

    # Check 2: Chunk count
    count_result = c.count(collection_name=collection, exact=True)
    chunk_count = count_result.count
    print(f"Check 1 — Chunk count: {chunk_count}")
    if not (min_chunks <= chunk_count <= max_chunks):
        msg = f"  FAIL: Expected {min_chunks}-{max_chunks} chunks, got {chunk_count}"
        failures.append(msg)
        print(msg)
    else:
        print(f"  PASS: {chunk_count} chunks in target range [{min_chunks}, {max_chunks}]")

    # Check 3: Sample 5 payloads
    scroll_result = c.scroll(collection_name=collection, limit=20, with_payload=True)
    points = scroll_result[0]

    if not points:
        failures.append("FAIL: Collection is empty (no points to sample)")
        print("FAIL: Collection is empty")
    else:
        # Pick 5 evenly-spaced samples
        step = max(1, len(points) // 5)
        samples = points[::step][:5]
        print(f"\nCheck 2 — Payload schema (sampling {len(samples)} points):")

        for i, pt in enumerate(samples):
            payload = pt.payload or {}
            missing = REQUIRED_FIELDS - set(payload.keys())

            if missing:
                msg = f"  FAIL point {i}: missing fields {missing}"
                failures.append(msg)
                print(msg)
            else:
                print(f"  PASS point {i}: all {len(REQUIRED_FIELDS)} required fields present")

                # Check 4: page_start <= page_end
                ps = payload.get("page_start", 0)
                pe = payload.get("page_end", 0)
                if ps > pe:
                    msg = f"  FAIL point {i}: page_start ({ps}) > page_end ({pe})"
                    failures.append(msg)
                    print(msg)

                # Check 5: span_offsets[0] <= span_offsets[1]
                so = payload.get("span_offsets")
                if so is not None:
                    if isinstance(so, (list, tuple)) and len(so) == 2:
                        if so[0] > so[1]:
                            msg = f"  FAIL point {i}: span_offsets[0] ({so[0]}) > span_offsets[1] ({so[1]})"
                            failures.append(msg)
                            print(msg)
                    else:
                        msg = f"  FAIL point {i}: span_offsets has unexpected format: {so}"
                        failures.append(msg)
                        print(msg)

                # Check 6: printed_page_label non-empty
                ppl = payload.get("printed_page_label", "")
                if not ppl:
                    msg = f"  FAIL point {i}: printed_page_label is empty"
                    failures.append(msg)
                    print(msg)

    # Check 7: Index size estimate
    from storage.vector import EMBEDDING_DIM

    print("\nCheck 3 — Index size estimate:")
    raw_vector_bytes = chunk_count * EMBEDDING_DIM * 4
    payload_bytes_estimate = chunk_count * 512
    total_bytes = raw_vector_bytes + payload_bytes_estimate
    total_mb = total_bytes / (1024 * 1024)
    utilization = total_mb / QDRANT_FREE_TIER_MB * 100

    print(f"  Estimated size: {total_mb:.1f} MB / {QDRANT_FREE_TIER_MB} MB ({utilization:.1f}%)")
    if utilization > WARN_UTILIZATION_PCT:
        print(f"  WARNING: > {WARN_UTILIZATION_PCT}% utilization of Qdrant free tier")

    # Final result
    print("\n" + "=" * 50)
    if failures:
        print(f"RESULT: FAILED — {len(failures)} check(s) failed")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"RESULT: PASSED — all checks pass")
        print(
            f"  Collection '{collection}': {chunk_count} chunks, "
            f"{total_mb:.1f} MB ({utilization:.1f}% utilized)"
        )


if __name__ == "__main__":
    app()
