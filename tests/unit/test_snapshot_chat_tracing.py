"""Regression guard for EVAL-05: the production chat path must be traced.

The eval-review audit (06.1-EVAL-REVIEW.md) found that ``ui/snapshot_chat.py`` called
``graph.invoke()`` directly, bypassing ``agent.graph.invoke_with_tracing`` — so real user
queries produced NO Langfuse trace despite the phase's "+ Langfuse Ops". This test pins the
fix so the untraced path cannot silently return: the production chat MUST route through
``invoke_with_tracing`` (which emits the enriched direct-API trace and no-ops when keys are
unset). AST-based so it ignores comments/docstrings that mention ``graph.invoke()``.
"""
from __future__ import annotations

import ast
import inspect

import ui.snapshot_chat as snapshot_chat


def test_production_chat_routes_through_invoke_with_tracing() -> None:
    tree = ast.parse(inspect.getsource(snapshot_chat))

    # No bare `<x>.invoke(...)` call may remain — that is exactly the untraced bypass
    # (graph.invoke / GRAPH.invoke) the audit flagged. invoke_with_tracing is a Name call,
    # not an Attribute `.invoke`, so this catches the regression without false positives.
    bare_invoke = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "invoke"
    ]
    assert not bare_invoke, (
        "ui/snapshot_chat.py must not call <graph>.invoke() directly — route the production "
        "chat through invoke_with_tracing so every user query emits a Langfuse trace (EVAL-05)."
    )

    # invoke_with_tracing IS called on the chat path.
    traced_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "invoke_with_tracing"
    ]
    assert traced_calls, (
        "ui/snapshot_chat.py must call invoke_with_tracing(state, question) so production "
        "queries are traced (EVAL-05)."
    )

    # The untraced build_graph() entry point must not be re-imported into this module.
    assert hasattr(snapshot_chat, "invoke_with_tracing")
    assert not hasattr(snapshot_chat, "build_graph"), (
        "the untraced build_graph() path must not be re-imported into snapshot_chat"
    )
