"""
Unit test — the GMP-02 isolation pin (D4-03).

Grey-market premium is a read-only, cache-only DISPLAY signal. It must never be
allowed to leak into the downstream prediction pipeline. This test copies the
Phase 3 import-audit pattern (tests/unit/test_methodology_pane.py::
test_no_llm_or_qdrant_import + tests/unit/test_cite_check.py::
test_no_llm_judge_fallback): it reads each GMP module's source via
inspect.getsource and asserts NONE of the forbidden model/prediction tokens
appear — a substring audit that fails loudly the moment GMP code references any
modelling library or the Phase 5 prediction/historical modules.

(Phase 5 owns the reverse audit: the predictor must not import pipelines.gmp.)
"""
from __future__ import annotations

import inspect

import agent.gmp_schema

# Forbidden substrings: any modelling library or downstream prediction/historical
# module the GMP display layer must stay computationally isolated from (GMP-02,
# D4-03). Keeping this list as literal substrings mirrors the proven Phase 3
# inspect.getsource audit.
FORBIDDEN_TOKENS = (
    "xgboost",
    "mapie",
    "sklearn",
    "forecast",
    "pipelines.features",
    "pipelines.historical",
    "GRAPH.invoke",
)


import pipelines.gmp
import pipelines.gmp_sources


def _gmp_modules():
    """The GMP modules under isolation audit.

    Both the schema (agent.gmp_schema) and the pipeline (pipelines.gmp +
    pipelines.gmp_sources) must stay computationally isolated from any modelling
    or downstream prediction/historical code (GMP-02, D4-03).
    """
    return [
        agent.gmp_schema,
        pipelines.gmp,
        pipelines.gmp_sources,
    ]


def test_gmp_modules_import_no_model_code() -> None:
    """agent.gmp_schema + pipelines.gmp + pipelines.gmp_sources reference NONE of
    the forbidden modelling/prediction tokens — GMP is display-only, cache-only."""
    for mod in _gmp_modules():
        src = inspect.getsource(mod)
        for token in FORBIDDEN_TOKENS:
            assert token not in src, (
                f"{mod.__name__} must not reference {token!r} "
                f"(GMP-02/D4-03: GMP is a read-only display signal, "
                f"computationally isolated from the prediction pipeline)."
            )
