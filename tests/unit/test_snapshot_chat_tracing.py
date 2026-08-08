"""Regression guard for EVAL-05: the production chat path must be traced.

The eval-review audit (06.1-EVAL-REVIEW.md) found that ``ui/snapshot_chat.py`` called
``graph.invoke()`` directly, bypassing the traced entry point — so real user queries
produced NO Langfuse trace despite the phase's "+ Langfuse Ops". This test pins the fix
so the untraced path cannot silently return.

Phase 6.3-08 (D-02/D-03) re-routes the production chat through the bounded MULTI-TOOL
``agent.supervisor.invoke_supervisor`` (which fuses one cited answer AND emits the same
enriched trace + ``flush`` internally, no-op when Langfuse keys are unset), replacing the
Phase-1 single-tool ``invoke_with_tracing``. The EVAL-05 invariant is unchanged — the
production chat routes through a TRACED entry point and never a bare ``.invoke()`` bypass.
AST-based so it ignores comments/docstrings that mention ``graph.invoke()``.
"""
from __future__ import annotations

import ast
import inspect

import ui.snapshot_chat as snapshot_chat


def test_production_chat_routes_through_traced_supervisor() -> None:
    tree = ast.parse(inspect.getsource(snapshot_chat))

    # No bare `<x>.invoke(...)` call may remain — that is exactly the untraced bypass
    # (graph.invoke / GRAPH.invoke / SUPERVISOR.invoke) the audit flagged. The traced
    # entry point is a Name call (`invoke_supervisor`), not an Attribute `.invoke`, so
    # this catches the regression without false positives.
    bare_invoke = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "invoke"
    ]
    assert not bare_invoke, (
        "ui/snapshot_chat.py must not call <graph>.invoke() directly — route the production "
        "chat through the traced invoke_supervisor so every user query emits a Langfuse "
        "trace (EVAL-05)."
    )

    # invoke_supervisor IS called on the chat path (the traced multi-tool entry point).
    traced_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "invoke_supervisor"
    ]
    assert traced_calls, (
        "ui/snapshot_chat.py must call invoke_supervisor(question, drhp_id) so production "
        "queries are traced AND fused across the multi-tool agent (EVAL-05 / D-03)."
    )

    # The traced entry point is imported; the untraced build_graph()/single-graph path
    # must not be re-imported into this module.
    assert hasattr(snapshot_chat, "invoke_supervisor")
    assert not hasattr(snapshot_chat, "build_graph"), (
        "the untraced build_graph() path must not be re-imported into snapshot_chat"
    )
    assert not hasattr(snapshot_chat, "invoke_with_tracing"), (
        "the Phase-1 single-tool invoke_with_tracing is superseded by the multi-tool "
        "supervisor (6.3-08 D-02/D-03); it must not linger as a second chat code path"
    )
