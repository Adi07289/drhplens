"""
DRHP binary integrity tests.

These tests verify the committed Swiggy DRHP prospectus PDF is intact and matches the
pinned SHA-256 checksum. They are NOT xfail stubs — they test real, committed artifacts
and must stay green from Wave 0 onward.

Implements REQ INGEST-01 (binary acquisition + cryptographic integrity pin).
Mitigates threat T-1-05-PDF (supply-chain tampering / malicious PDF substitution).
"""
from __future__ import annotations

import hashlib
import pathlib


DRHP_DIR = pathlib.Path("data/swiggy_drhp")
PDF_PATH = DRHP_DIR / "swiggy_prospectus_2024_11.pdf"
SHA256SUMS_PATH = DRHP_DIR / "SHA256SUMS"


def test_drhp_pdf_exists() -> None:
    """Assert the Swiggy prospectus PDF is committed to the repo."""
    assert PDF_PATH.exists(), (
        f"DRHP PDF not found at {PDF_PATH}. "
        "Run: curl -L -o data/swiggy_drhp/swiggy_prospectus_2024_11.pdf "
        "'https://www.sebi.gov.in/sebi_data/attachdocs/nov-2024/1731315962150.pdf'"
    )


def test_drhp_sha256_matches() -> None:
    """Assert the PDF's SHA-256 matches the pinned value in SHA256SUMS.

    Mitigates T-1-05-PDF: if the PDF is replaced by a tampered file (malicious content,
    wrong version, truncated download), this test fails CI and blocks the ingest pipeline.
    """
    assert SHA256SUMS_PATH.exists(), f"SHA256SUMS not found at {SHA256SUMS_PATH}"
    assert PDF_PATH.exists(), f"PDF not found at {PDF_PATH}"

    # Parse the expected hash from SHA256SUMS (GNU sha256sum format: "<hex>  <filename>")
    sha256sums_text = SHA256SUMS_PATH.read_text(encoding="utf-8").strip()
    lines = [line for line in sha256sums_text.splitlines() if line.strip()]
    assert len(lines) == 1, f"SHA256SUMS should contain exactly 1 line; got {len(lines)}"
    parts = lines[0].split(None, 1)
    assert len(parts) == 2, f"SHA256SUMS line malformed: {lines[0]!r}"
    expected_hex, pinned_filename = parts
    assert len(expected_hex) == 64, f"Expected 64-char SHA-256 hex; got {len(expected_hex)} chars"
    assert pinned_filename == "swiggy_prospectus_2024_11.pdf", (
        f"Unexpected filename in SHA256SUMS: {pinned_filename!r}"
    )

    # Compute actual SHA-256 over the committed PDF bytes
    actual_hex = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    assert actual_hex == expected_hex, (
        f"SHA-256 MISMATCH — PDF may have been tampered with or re-downloaded.\n"
        f"  Expected: {expected_hex}\n"
        f"  Actual:   {actual_hex}\n"
        f"If the PDF was intentionally updated, re-run:\n"
        f"  sha256sum data/swiggy_drhp/swiggy_prospectus_2024_11.pdf > data/swiggy_drhp/SHA256SUMS"
    )


def test_drhp_size_in_range() -> None:
    """Assert PDF size is in the expected range for a real prospectus (5 MB – 25 MB).

    Defends against accidental empty-file commits (size = 0) or stub replacements.
    Typical Swiggy prospectus: ~10–15 MB based on 01-RESEARCH.md A12.
    """
    assert PDF_PATH.exists(), f"PDF not found at {PDF_PATH}"
    file_size = PDF_PATH.stat().st_size
    assert 5_000_000 < file_size < 25_000_000, (
        f"PDF size {file_size:,} bytes is outside the expected 5 MB – 25 MB range. "
        f"Actual size: {file_size / 1_000_000:.1f} MB. "
        "Verify the file was downloaded correctly."
    )
