"""
ui/format_inr.py — the ONE shared Indian rupee formatter (D4-07, UI-04).

Single source of truth for rendering every ₹ amount app-wide. Renders with
Indian digit grouping (last three digits, then groups of two — 12,34,567, NOT
Western 1,234,567) + auto-scaled lakh↔crore by magnitude + a `None → "—"`
sentinel + negatives wrapped in parentheses (the inherited no-red convention
from snapshot_blocks._format_fin_value).

Returns a string ONLY — `tabular-nums` numeral alignment is applied by CSS at
render time, never here. This module re-implements grouping nowhere else: every
ad-hoc ₹ render site (catalogue card, financials table, metadata header, peer
table, GMP block) routes through `format_inr` so the latent Western-grouping
FLAG-FORMAT bug cannot spread (D4-07 = ONE utility).

Threat: T-04-02-INJ (accept). The output is a formatted numeric string (digits,
₹, commas, parentheses) with no user-controlled text; callers html.escape any
adjacent untrusted strings. No injection surface.
"""
from __future__ import annotations


def _group_indian(int_str: str) -> str:
    """Indian digit grouping: '1234567' -> '12,34,567' (last 3, then groups of 2).

    Operates on a non-negative integer string with no sign or decimal point.
    """
    if len(int_str) <= 3:
        return int_str
    head, tail = int_str[:-3], int_str[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    parts.insert(0, head)
    return ",".join(parts) + "," + tail


def _trim_and_group(x: float) -> str:
    """Format a scaled lakh/crore value: up to 2 decimals with trailing zeros
    trimmed, and Indian grouping applied to the integer part (A8).

    12.50 -> '12.5'; 1247.00 -> '1,247'; 12.47 -> '12.47'.
    """
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    if "." in s:
        int_part, dec_part = s.split(".")
        return f"{_group_indian(int_part)}.{dec_part}"
    return _group_indian(s)


def format_inr(amount: float | int | None) -> str:
    """Render a rupee amount with Indian grouping + auto-scaled lakh/crore.

    - `None` -> "—" (missing sentinel, D4-07)
    - `>= ₹1,00,00,000` (1e7) -> "₹{x/1e7} crore" (integer part Indian-grouped)
    - `>= ₹1,00,000` (1e5)    -> "₹{x/1e5} lakh"
    - else                    -> "₹{Indian-grouped rupees}"
    - negatives wrap in parentheses in the same (no-red) colour as profits

    Returns a string only; CSS applies `tabular-nums` at render.
    """
    if amount is None:
        return "—"
    neg = amount < 0
    a = abs(amount)
    if a >= 1e7:
        s = f"₹{_trim_and_group(a / 1e7)} crore"
    elif a >= 1e5:
        s = f"₹{_trim_and_group(a / 1e5)} lakh"
    else:
        s = f"₹{_group_indian(str(int(round(a))))}"
    return f"({s})" if neg else s
