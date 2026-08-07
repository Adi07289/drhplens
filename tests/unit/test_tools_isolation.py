"""
Unit test — the tool-isolation pin (D-01): the read-only tools import NO model/LLM code.

Mirrors tests/unit/test_gmp_isolation.py 1:1. The three `agent/tools/*` loader nodes
are pure read-only file I/O over committed `data/*.json` (D-01) — they call no model,
no LLM, and burn no quota (the ONLY LLM authority in the supervisor is the single
clamped classify hop). This `inspect.getsource` substring audit fails LOUDLY the
moment any tool source references a modelling library or an LLM client — e.g. adding
`import xgboost` or `import instructor` to a tool would break this test.

It also pins the D-04 / P4 GMP invariant: `query_forecast` may reference GMP ONLY
via the display-only `GmpRecord` / `gmp_gap` path, never routing a GMP value into a
numeric model. Because the FORBIDDEN_TOKENS scan already forbids every modelling /
LLM symbol from the tool source, a future edit that tried to leak GMP into a model
computation would have to import one of those symbols — and would fail here.
"""
from __future__ import annotations

import inspect

import agent.tools.query_forecast
import agent.tools.query_peers
import agent.tools.query_redflags

# Forbidden substrings: any modelling library or LLM-client / graph-invocation symbol
# the read-only tool surface must stay isolated from (D-01). NOTE the data-domain
# words "forecast" / "peers" / "redflag" / "gmp" are NOT forbidden — they are the
# committed data the tools legitimately READ; only MODEL / LLM code is forbidden.
FORBIDDEN_TOKENS = (
    "xgboost",
    "lightgbm",
    "mapie",
    "sklearn",
    "scikit",
    "instructor",
    "genai",                 # google.genai / from google import genai (LLM client)
    "get_llm_client",
    "GRAPH.invoke",
    "agent.graph",           # the compiled LLM cite-Q&A graph
    "pipelines.features",
    "pipelines.historical",
    "ChatGoogle",
)


def _tool_modules():
    """The read-only tool modules under isolation audit (D-01)."""
    return [
        agent.tools.query_peers,
        agent.tools.query_forecast,
        agent.tools.query_redflags,
    ]


def test_tools_import_no_model_or_llm_code():
    """agent/tools/* reference NONE of the forbidden modelling/LLM tokens — the
    tools are pure read-only file I/O, zero model calls, zero quota (D-01)."""
    for mod in _tool_modules():
        src = inspect.getsource(mod)
        for token in FORBIDDEN_TOKENS:
            assert token not in src, (
                f"{mod.__name__} must not reference {token!r} "
                f"(D-01: the read-only tools call no model/LLM and burn no quota; "
                f"the only LLM authority is the single classify hop)."
            )


def test_query_forecast_references_gmp_only_via_display_path():
    """query_forecast surfaces GMP ONLY through the display-only GmpRecord/gmp_gap
    path, never as a model feature (D-04 / P4)."""
    src = inspect.getsource(agent.tools.query_forecast)

    # GMP is present, but ONLY via the read-only display record + the gap block.
    assert "GmpRecord" in src, "query_forecast must read GMP via the display-only GmpRecord."
    assert "gmp_gap" in src, "query_forecast must surface GMP only as the display gmp_gap."

    # Belt-and-suspenders: no modelling/LLM token in the source, so a GMP value can
    # not reach any model computation from this module (D-04/P4 leak-guard).
    for token in FORBIDDEN_TOKENS:
        assert token not in src, (
            f"query_forecast must not reference {token!r} — GMP stays display-only, "
            f"never a model feature (D-04/P4)."
        )
