"""
Unit test stub — pipelines/ingest.py(drhp_id, pdf_path, metadata) parameterized (no threat).

Requirement: INGEST (reuse). Threat: none.
Secure behavior: pipelines/ingest.py(drhp_id, pdf_path, metadata) is parameterized;
no module-level hard-codes remain (generalized from pipelines/ingest_swiggy.py).

Wave 0 stub — Wave 2 implements (02-VALIDATION.md row "2-ingest-generalize").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 2 — not yet implemented", strict=False)
def test_ingest_drhp_accepts_drhp_id_and_pdf_path() -> None:
    raise NotImplementedError
