"""
pipelines/features/build.py — issue-structure feature matrix behind the T0 gate.

``build_features(panel)`` turns the survivorship-corrected historical panel into
the model's design matrix ``X`` (FEATURE_COLUMNS) plus a parallel ``available_at``
matrix, behind a **hard ``available_at <= T0`` leakage gate** where ``T0`` is the
issue-open day (``issue_date``, D5-01). If ANY feature's resolved ``available_at``
for ANY row is *after* that row's ``issue_date``, the build RAISES ``LeakageError``
(naming the offending feature + issuer) — the primary P4/lookahead defense
(FCAST-02, T-05-04-LEAK). This mirrors ``assemble_panel``'s invalid-status raise:
a malformed/leaking row is caught and named, never silently coerced.

Honesty grammar copied from ``pipelines.historical.assemble_panel``:
  * **replace-with-NaN** — a missing issue-structure value is coerced to ``NaN``
    (retained, counted), never fabricated as 0; the row count is preserved
    (T-05-04-FAB).
  * **excluded-by-construction** — the builder asserts none of
    ``EXCLUDED_FROM_MODEL`` (GMP / at-close subscription / listing-day price) is
    ever a built column (T-05-04-EXCL).

``leakage_audit(panel)`` returns, per feature, ``{feature, available_at_rule,
verdict}`` — all ``"<= T0 ✓"`` for the issue-structure slice — as the FCAST-02
model-card audit. Its plain-data posture mirrors
``pipelines.historical.validate.sanity_check_median`` (a statistic + a
``/methodology``-ready plain-text record, not a UI widget).

available_at resolution (per feature, per row), in priority order:
  1. a per-feature override column ``f"{feature}__available_at"`` in the panel, else
  2. a shared ``filing_date`` column in the panel, else
  3. a shared ``available_at`` stamp column (the one the 05-01
     ``synthetic_features`` fixture emits, == issue_date), else
  4. the panel's ``issue_date`` itself (the conservative T0 anchor — the DRHP/RHP
     is filed on or before issue open, so ``filing_date <= issue_date`` holds and
     using ``issue_date`` never *understates* availability).
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from pipelines.features import (
    EXCLUDED_FROM_MODEL,
    EXCLUDED_SUBSTRINGS,
    FEATURE_AVAILABLE_AT,
    FEATURE_COLUMNS,
    FEATURE_DTYPES,
    T0_COLUMN,
)


class LeakageError(ValueError):
    """A feature's ``available_at`` resolves AFTER T0 (issue-open) for some row.

    Raised by ``build_features`` when the ``available_at <= issue_date`` gate is
    violated — i.e. a look-ahead feature slipped in (FCAST-02 / P4). The message
    names the offending feature + issuer, mirroring ``assemble_panel``'s
    invalid-status raise.
    """


def _to_float_or_nan(value: Any) -> float:
    """Replace-with-NaN coercion (mirrors ``pipelines.historical._to_float_or_nan``).

    A missing / uncoercible value becomes ``float('nan')`` — an HONEST absence to be
    RETAINED and counted, never fabricated as 0.
    """
    if value is None:
        return float("nan")
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return f


def _assert_no_excluded_columns(columns: list[str]) -> None:
    """Guard the FCAST-02 exclusion invariant (T-05-04-EXCL).

    Assert no built column is (or contains) a GMP / subscription / listing-day
    token. Raises ``ValueError`` on violation — GMP and at-close subscription can
    NEVER be a feature by construction.
    """
    lowered = {c: c.lower() for c in columns}
    for col, low in lowered.items():
        if low in EXCLUDED_FROM_MODEL:
            raise ValueError(
                f"Excluded token {col!r} may NEVER be a model feature "
                f"(FCAST-02: GMP / at-close subscription / listing-day price)."
            )
        for token in EXCLUDED_SUBSTRINGS:
            if token in low:
                raise ValueError(
                    f"Built column {col!r} contains excluded token {token!r}; "
                    f"GMP / subscription / listing-day signals are barred features "
                    f"by construction (FCAST-02)."
                )


def _resolve_available_at(panel: pd.DataFrame, feature: str) -> pd.Series:
    """Resolve the per-row ``available_at`` datetime for one feature.

    Priority: per-feature override column ``f"{feature}__available_at"`` ->
    shared ``filing_date`` column -> shared ``available_at`` stamp (the 05-01
    ``synthetic_features`` fixture) -> the panel's ``issue_date`` (T0 anchor).
    Coerced to ``datetime64[ns]`` (an uncoercible/missing stamp becomes ``NaT``).
    """
    override = f"{feature}__available_at"
    if override in panel.columns:
        source = panel[override]
    elif "filing_date" in panel.columns:
        source = panel["filing_date"]
    elif "available_at" in panel.columns:
        source = panel["available_at"]
    else:
        source = panel[T0_COLUMN]
    return pd.to_datetime(source, errors="coerce")


def build_features(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the issue-structure feature matrix behind the T0 leakage gate.

    Derives each ``FEATURE_COLUMNS`` value from the panel (replace-with-NaN for a
    missing/absent source), resolves each feature's ``available_at`` per row, and
    ASSERTS ``available_at <= issue_date`` (T0) for every feature of every row —
    raising ``LeakageError`` (naming the feature + issuer) on any violation.

    Args:
        panel: an assembled historical panel (see ``pipelines.historical``) — must
            carry the ``issue_date`` (T0) column. Issue-structure feature values
            and optional ``filing_date`` / ``<feature>__available_at`` columns are
            read when present; absent feature columns yield NaN (retained, counted).

    Returns:
        ``(X, available_at)``:
          - ``X`` — a DataFrame with exactly ``FEATURE_COLUMNS`` (float64), one row
            per panel row (row count preserved), missing values NaN-retained.
          - ``available_at`` — a parallel DataFrame with the same ``FEATURE_COLUMNS``
            holding each feature's resolved ``available_at`` datetime per row.

    Raises:
        ValueError: if the panel lacks the ``issue_date`` (T0) column, or an
            excluded token (GMP / subscription / listing-day) is a built column.
        LeakageError: if any feature's ``available_at`` > ``issue_date`` (T0) for
            any row (FCAST-02 / P4 look-ahead leakage).
    """
    if T0_COLUMN not in panel.columns:
        raise ValueError(
            f"Panel is missing the T0 column {T0_COLUMN!r}; cannot enforce the "
            f"available_at <= T0 leakage gate."
        )

    # Guard the exclusion invariant BEFORE building anything (T-05-04-EXCL).
    _assert_no_excluded_columns(list(FEATURE_COLUMNS))

    t0 = pd.to_datetime(panel[T0_COLUMN], errors="coerce")

    x_data: dict[str, list[float]] = {}
    avail_data: dict[str, pd.Series] = {}

    for feature in FEATURE_COLUMNS:
        # Feature value: read from the panel when present, else NaN (retained).
        if feature in panel.columns:
            x_data[feature] = [_to_float_or_nan(v) for v in panel[feature]]
        else:
            x_data[feature] = [float("nan")] * len(panel)

        # available_at: resolve per row and enforce the hard T0 gate.
        avail = _resolve_available_at(panel, feature)
        avail.index = panel.index
        # Leakage iff available_at is known AND after T0 (issue-open). A NaT stamp
        # or NaT T0 is not counted as leakage (nothing to compare) — the gate is a
        # positive assertion of a violation, never a coerced pass.
        violation = avail.notna() & t0.notna() & (avail > t0)
        if bool(violation.any()):
            first = violation[violation].index[0]
            issuer = (
                panel.loc[first, "issuer"] if "issuer" in panel.columns else "<unknown>"
            )
            n_bad = int(violation.sum())
            raise LeakageError(
                f"Look-ahead leakage: feature {feature!r} for issuer {issuer!r} "
                f"(row {first}) resolves available_at={avail.loc[first]!r} which is "
                f"AFTER T0 (issue_date={t0.loc[first]!r}). {n_bad} row(s) violate the "
                f"available_at <= T0 gate (FCAST-02 / D5-01)."
            )
        avail_data[feature] = avail

    x = pd.DataFrame(x_data, index=panel.index)
    x = x.loc[:, list(FEATURE_COLUMNS)].astype(FEATURE_DTYPES)

    available_at = pd.DataFrame(avail_data, index=panel.index)
    available_at = available_at.loc[:, list(FEATURE_COLUMNS)]

    # Final belt-and-braces exclusion guard on the actually-built columns.
    _assert_no_excluded_columns(list(x.columns))

    return x, available_at


def leakage_audit(panel: pd.DataFrame | None = None) -> list[dict[str, str]]:
    """Emit the FCAST-02 leakage audit for the model card (plain-data records).

    Returns one record per feature: ``{feature, available_at_rule, verdict}``.
    Every issue-structure feature is filing-date-anchored (``available_at <= T0``),
    so every verdict is ``"<= T0 ✓"``. No GMP / subscription feature can appear
    (they are excluded by construction).

    When ``panel`` is provided the audit is DATA-VERIFIED: ``build_features(panel)``
    is run first, so a leaking panel raises ``LeakageError`` rather than emitting a
    falsely-clean audit. When ``panel`` is None the audit is the static declaration
    (usable for the model card without a live panel).

    Args:
        panel: an optional assembled panel to data-verify the gate against.

    Returns:
        A list of ``{feature, available_at_rule, verdict}`` dicts, one per
        ``FEATURE_COLUMNS`` feature, in feature order.

    Raises:
        LeakageError: if ``panel`` is given and any feature violates the T0 gate.
        ValueError: if an excluded token is a built column (should be impossible).
    """
    if panel is not None:
        # Data-verify: this RAISES on any real leakage, keeping the audit honest.
        build_features(panel)

    audit: list[dict[str, str]] = []
    for feature in FEATURE_COLUMNS:
        rule = FEATURE_AVAILABLE_AT[feature]
        # A feature can never be an excluded token — assert it here so the audit
        # itself is a guard, not just a report.
        if feature.lower() in EXCLUDED_FROM_MODEL or any(
            tok in feature.lower() for tok in EXCLUDED_SUBSTRINGS
        ):  # pragma: no cover - FEATURE_COLUMNS is curated to exclude these
            raise ValueError(
                f"Audit invariant breached: feature {feature!r} is an excluded token."
            )
        audit.append(
            {
                "feature": feature,
                "available_at_rule": rule,
                "verdict": "<= T0 ✓",
            }
        )
    return audit


__all__ = [
    "LeakageError",
    "build_features",
    "leakage_audit",
]
