"""
Adoption gate (D4-07 / UI-04 / FLAG-FORMAT): every ₹ render in ui/ routes through
ui.format_inr.format_inr — no module re-implements digit grouping, and the latent
Western-grouping bug (`f"₹{n:,} cr"`) cannot reappear.

AST-based, not text-grep: a docstring/comment that merely *documents* the old
`f"₹{n:,}"` pattern is a plain string Constant, not an f-string (ast.JoinedStr),
so it is correctly ignored. Only a real f-string containing '₹' whose FormattedValue
applies a ',' grouping format spec counts as a violation.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import ui.catalogue as catalogue
import ui.snapshot_blocks as snapshot_blocks

UI_DIR = Path(__file__).resolve().parents[2] / "ui"


def _joinedstr_literal(node: ast.JoinedStr) -> str:
    return "".join(
        v.value
        for v in node.values
        if isinstance(v, ast.Constant) and isinstance(v.value, str)
    )


def _western_grouped_rupee_fstrings(source: str) -> list[str]:
    """Offending snippets: an f-string containing '₹' with a ',' group-spec."""
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        if "₹" not in _joinedstr_literal(node):
            continue
        for value in node.values:
            if isinstance(value, ast.FormattedValue) and value.format_spec is not None:
                spec = "".join(
                    c.value
                    for c in value.format_spec.values
                    if isinstance(c, ast.Constant) and isinstance(c.value, str)
                )
                if "," in spec:
                    offenders.append(_joinedstr_literal(node))
    return offenders


def test_no_western_grouped_rupee_fstring_in_ui() -> None:
    """No ui/*.py may render a ₹ amount with a bare Western ',' group-spec —
    grouping lives in exactly one place (format_inr)."""
    violations: dict[str, list[str]] = {}
    for py in sorted(UI_DIR.glob("*.py")):
        offenders = _western_grouped_rupee_fstrings(py.read_text(encoding="utf-8"))
        if offenders:
            violations[py.name] = offenders
    assert not violations, (
        "Western-grouped ₹ f-strings must delegate to ui.format_inr.format_inr "
        f"instead (D4-07 = ONE utility): {violations}"
    )


def test_rupee_call_sites_delegate_to_format_inr() -> None:
    """The two known ₹ render sites route through format_inr (not re-implemented)."""
    assert "format_inr" in inspect.getsource(catalogue._format_issue_size)
    assert "format_inr" in inspect.getsource(snapshot_blocks._format_fin_value)
