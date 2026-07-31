"""
pipelines/features/build.py — the four-family feature matrix behind the T0 gate.

``build_features(panel)`` turns the survivorship-corrected historical panel into
the model's design matrix ``X`` (FEATURE_COLUMNS — all four D5-06 families) plus a
parallel ``available_at`` matrix, behind a **hard ``available_at <= T0`` leakage
gate** where ``T0`` is the issue-open day (``issue_date``, D5-01). If ANY feature's
resolved ``available_at`` for ANY row is *after* that row's ``issue_date``, the
build RAISES ``LeakageError`` (naming the offending feature + issuer) — the primary
P4/lookahead defense (FCAST-02, T-05-08-LEAK). This mirrors ``assemble_panel``'s
invalid-status raise: a malformed/leaking row is caught and named, never silently
coerced.

The four candidate families (D5-06), each stamped ``available_at <= T0``:
  * (a) issue structure — read from the panel (filing date).
  * (b) market regime — ``ipo_pipeline_density`` / ``trailing_listing_gain`` are
    PANEL-DERIVED strictly from PRIOR listings (no lookahead); ``nifty_mom_*`` /
    ``india_vix`` come from the live-deferred fetchers (read from the panel when
    written, else NaN). Available at the pre-open (T0-1) snapshot.
  * (c) DRHP-derived — read allow-list-gated from ``data/snapshots`` (Phase 2) +
    ``data/redflag`` (Phase 3); numbers come ONLY from a clean structured
    ``"numeric"`` block + the ``ranked_risks`` count, never prose-parsed
    (T-05-08-PATH gate before any path; T-05-08-FAB replace-with-NaN).
  * (d) anchor demand — read from the pre-open anchor allocation ONLY
    (``anchor_leakage_audit``, D5-08); post-open QIB/NII/RII subscription is
    excluded by construction and asserted absent.

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

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from data.catalogue_loader import is_known_drhp_id
from pipelines.features import (
    ANCHOR_FEATURES,
    AVAILABLE_AT_PREOPEN,
    DRHP_FEATURES,
    EXCLUDED_FROM_MODEL,
    EXCLUDED_SUBSTRINGS,
    FEATURE_AVAILABLE_AT,
    FEATURE_COLUMNS,
    FEATURE_DTYPES,
    FEATURE_FAMILY,
    REGIME_FEATURES,
    T0_COLUMN,
)

# ---------------------------------------------------------------------------
# DRHP-derived (family c) cache directories (allow-list-gated reads, T-05-08-PATH).
# Module-level so tests can point them at a tmp fixture dir; the id is ALWAYS
# gated through is_known_drhp_id BEFORE either path is formed (path-traversal).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS_DIR: Path = _REPO_ROOT / "data" / "snapshots"  # Phase 2 financials cache
REDFLAG_DIR: Path = _REPO_ROOT / "data" / "redflag"      # Phase 3 NLP extraction cache

# Regime panel-derivation windows (D5-06b) — computed strictly from PRIOR listings.
REGIME_PIPELINE_WINDOW_DAYS: int = 90  # trailing ~3-month IPO-pipeline density window
TRAILING_LISTING_N: int = 12           # trailing-N listings for the mean listing gain

# The exact pre-open anchor source field per anchor feature (D5-08 audit surface).
_ANCHOR_SOURCE_FIELDS: dict[str, str] = {
    "anchor_book_cr": "pre-open anchor allocation book size (₹ crore)",
    "anchor_investor_quality": "pre-open anchor-investor quality/mix score",
    "anchor_lockin_frac": "pre-open anchor lock-in fraction",
}
# The post-open subscription multiples that can NEVER be a feature (D5-08). They
# close AFTER issue open (> T0); the pre-open anchor allocation is the ONLY anchor
# signal read. Named in EXCLUDED_FROM_MODEL and asserted absent by the builder.
_POST_OPEN_SUBSCRIPTION: tuple[str, ...] = ("subscription_at_close", "qib", "nii", "rii")


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


def _read_cache_json(path: Path) -> dict:
    """Read a committed cache JSON; return ``{}`` on any miss (honest absence).

    A missing / unparseable cache is an HONEST absence (→ NaN-retained features),
    never an error and never a fabricated value. Never called before the
    ``is_known_drhp_id`` allow-list gate (path-traversal, T-05-08-PATH).
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _read_drhp_numeric(drhp_id: str) -> dict[str, float]:
    """Read the DRHP-derived (family c) numerics for one issuer (allow-list gated).

    The ``drhp_id`` is checked against the catalogue allow-list BEFORE any path is
    formed (T-05-08-PATH path-traversal). Reads Phase-2 financials
    (``data/snapshots/<id>.json``) + Phase-3 NLP extraction
    (``data/redflag/<id>.json``).

    HONESTY: numbers are read ONLY from a clean structured ``"numeric"`` block (the
    forward-compatible extraction contract the real Phase-2/3 numeric build fills at
    05-11) plus ``red_flag_count`` derived from the Phase-3 ``ranked_risks`` count.
    Grounded-prose answers are NEVER parsed for numbers (that would fabricate a
    figure the extraction never structured). Anything absent stays ``NaN`` (retained).
    """
    result: dict[str, float] = {name: float("nan") for name in DRHP_FEATURES}

    # ALLOW-LIST GATE — refuse to form a path for an unknown/adversarial id.
    if not is_known_drhp_id(drhp_id):
        return result

    snap = _read_cache_json(SNAPSHOTS_DIR / f"{drhp_id}.json")
    red = _read_cache_json(REDFLAG_DIR / f"{drhp_id}.json")

    # Clean structured numerics only (never prose-parsed). Absent today -> NaN.
    for src in (snap, red):
        numeric = src.get("numeric") if isinstance(src, dict) else None
        if isinstance(numeric, dict):
            for name in DRHP_FEATURES:
                if name in numeric:
                    result[name] = _to_float_or_nan(numeric[name])

    # The one signal cleanly derivable from today's grounded caches: the COUNT of
    # ranked red-flags (a structured list length, not a prose-parsed number).
    if isinstance(red, dict) and isinstance(red.get("ranked_risks"), list):
        result["red_flag_count"] = float(len(red["ranked_risks"]))

    return result


def _derive_drhp_features(panel: pd.DataFrame) -> dict[str, list[float]]:
    """Derive family (c) DRHP-derived values per row (cache reads, memoized).

    Reads each row's ``drhp_id`` (when the panel carries one) through the
    allow-list-gated cache reader. Rows with no / unknown id keep NaN (retained).
    """
    n = len(panel)
    out: dict[str, list[float]] = {name: [float("nan")] * n for name in DRHP_FEATURES}
    if "drhp_id" not in panel.columns:
        return out

    cache: dict[str, dict[str, float]] = {}
    for pos, raw_id in enumerate(panel["drhp_id"]):
        if raw_id is None or (isinstance(raw_id, float) and math.isnan(raw_id)):
            continue
        drhp_id = str(raw_id)
        if drhp_id not in cache:
            cache[drhp_id] = _read_drhp_numeric(drhp_id)
        vals = cache[drhp_id]
        for name in DRHP_FEATURES:
            out[name][pos] = vals[name]
    return out


def _derive_regime_features(panel: pd.DataFrame) -> dict[str, list[float]]:
    """Derive the two PANEL-DERIVED regime features (family b) — no lookahead.

    ``ipo_pipeline_density`` — the count of PRIOR listings (``listing_date < T0_i``)
    within a trailing ``REGIME_PIPELINE_WINDOW_DAYS`` window of T0_i.
    ``trailing_listing_gain`` — the mean listing-day return of the ``TRAILING_LISTING_N``
    most-recent PRIOR listings (``listing_date < T0_i``).

    Both use ONLY IPOs that listed strictly before this IPO's issue-open day (T0),
    so they are genuinely available at the pre-open (T0-1) snapshot — no future IPO
    can leak in (P4). A row with no prior listings keeps NaN gain (honest — nothing
    to average); its density is an honest 0 (no prior listings in the window). The
    other regime features (``nifty_mom_*``/``india_vix``) come from the live-deferred
    fetchers and are read from the panel when present, else NaN.
    """
    n = len(panel)
    density = [float("nan")] * n
    trailing = [float("nan")] * n
    if not {"listing_date", "issue_date"} <= set(panel.columns):
        return {"ipo_pipeline_density": density, "trailing_listing_gain": trailing}

    listing = pd.to_datetime(panel["listing_date"], errors="coerce")
    issue = pd.to_datetime(panel["issue_date"], errors="coerce")
    if "listing_day_return" in panel.columns:
        ret = pd.to_numeric(panel["listing_day_return"], errors="coerce")
    else:
        ret = pd.Series([float("nan")] * n, index=panel.index)

    for pos in range(n):
        t0 = issue.iloc[pos]
        if pd.isna(t0):
            continue
        prior = listing < t0  # STRICT no-lookahead: listed before this IPO's T0
        window_start = t0 - pd.Timedelta(days=REGIME_PIPELINE_WINDOW_DAYS)
        density[pos] = float(int((prior & (listing >= window_start)).sum()))
        prior_idx = listing[prior].sort_values().index[-TRAILING_LISTING_N:]
        prior_returns = ret.loc[prior_idx].dropna()
        if len(prior_returns) > 0:
            trailing[pos] = float(prior_returns.mean())

    return {"ipo_pipeline_density": density, "trailing_listing_gain": trailing}


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
    """Resolve the per-row ``available_at`` datetime for one feature (rule-aware).

    A per-feature override column ``f"{feature}__available_at"`` ALWAYS wins (used
    by the leakage tests to craft a post-T0 stamp). Otherwise the feature's
    ``FEATURE_AVAILABLE_AT`` rule decides:

      * ``AVAILABLE_AT_PREOPEN`` (regime family b + anchor family d) -> the pre-open
        (T0-1 EOD) snapshot = ``issue_date - 1 day`` (strictly < T0). Regime = the
        NIFTY/VIX/pipeline snapshot taken the evening before issue open; anchor =
        the allocation disclosed T0-1. This is the honest, data-true stamp for a
        pre-open feature — never the shared issue-structure stamp.
      * else (filing rule, family a + c) -> shared ``filing_date`` column ->
        shared ``available_at`` stamp (the 05-01 ``synthetic_features`` fixture) ->
        the panel's ``issue_date`` (the conservative T0 anchor).

    Coerced to ``datetime64[ns]`` (an uncoercible/missing stamp becomes ``NaT``).
    """
    override = f"{feature}__available_at"
    if override in panel.columns:
        return pd.to_datetime(panel[override], errors="coerce")

    rule = FEATURE_AVAILABLE_AT.get(feature)
    if rule == AVAILABLE_AT_PREOPEN:
        # Pre-open (T0-1 EOD) snapshot — strictly the day before issue open.
        t0 = pd.to_datetime(panel[T0_COLUMN], errors="coerce")
        return t0 - pd.Timedelta(days=1)

    if "filing_date" in panel.columns:
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

    # Pre-compute the panel-derived (regime b) + cache-derived (DRHP c) families
    # once. These take precedence over a same-named raw panel column: regime
    # density/gain are computed no-lookahead from PRIOR listings, and family (c)
    # numbers come from the allow-list-gated DRHP caches — never a raw panel column.
    regime_derived = _derive_regime_features(panel)
    drhp_derived = _derive_drhp_features(panel)

    x_data: dict[str, list[float]] = {}
    avail_data: dict[str, pd.Series] = {}

    for feature in FEATURE_COLUMNS:
        # Feature value resolution, in precedence order:
        #   1. panel-derived regime (b): ipo_pipeline_density / trailing_listing_gain
        #   2. cache-derived DRHP (c): allow-list-gated data/snapshots + data/redflag
        #   3. a raw panel column (family a issue-structure; family d anchor pre-open
        #      allocation; live-deferred nifty/vix when the fetchers have written them)
        #   4. else NaN (retained, counted — never fabricated 0).
        if feature in regime_derived:
            x_data[feature] = regime_derived[feature]
        elif feature in drhp_derived:
            x_data[feature] = drhp_derived[feature]
        elif feature in panel.columns:
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

    # Guard the D5-08 anchor invariant even in the static declaration: post-open
    # subscription can never be a feature (raises if that ever regresses).
    anchor_leakage_audit()

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
                "family": FEATURE_FAMILY.get(feature, "?"),
                "available_at_rule": rule,
                "verdict": "<= T0 ✓",
            }
        )
    return audit


def anchor_leakage_audit() -> list[dict[str, str]]:
    """The EXPLICIT pre-open anchor leakage audit (D5-08).

    Anchor-investor demand is the ONE legitimate T0 demand proxy, but it is
    BORDERLINE: the anchor allocation is disclosed the day BEFORE issue open
    (T0-1), so it is legitimately ``<= T0`` — *provided* only the pre-open
    allocation is read, never the post-open QIB/NII/RII subscription that closes
    AFTER issue open. This audit names, per anchor feature, the exact pre-open
    source field + its T0-1 disclosure timestamp + verdict, and ASSERTS the
    post-open subscription multiples can never be a feature.

    Returns:
        One ``{feature, source_field, disclosure_timestamp, verdict}`` record per
        anchor feature (family d).

    Raises:
        ValueError: if any post-open subscription multiple
            (``subscription_at_close`` / ``qib`` / ``nii`` / ``rii``) has leaked
            into ``FEATURE_COLUMNS`` or dropped out of ``EXCLUDED_FROM_MODEL``.
    """
    # Assert the post-open subscription multiples are excluded by construction.
    for token in _POST_OPEN_SUBSCRIPTION:
        if token in FEATURE_COLUMNS:
            raise ValueError(
                f"Anchor leakage: post-open subscription {token!r} may NEVER be a "
                f"feature — it closes AFTER issue open (> T0). Read ONLY the pre-open "
                f"anchor allocation (D5-08)."
            )
        if token not in EXCLUDED_FROM_MODEL:
            raise ValueError(
                f"Anchor audit invariant breached: {token!r} must stay named in "
                f"EXCLUDED_FROM_MODEL (post-open subscription, D5-08)."
            )

    return [
        {
            "feature": feature,
            "source_field": _ANCHOR_SOURCE_FIELDS[feature],
            "disclosure_timestamp": "T0-1",
            "verdict": "pre-open allocation only, <= T0 ✓",
        }
        for feature in ANCHOR_FEATURES
    ]


def pool_sectors(
    panel: pd.DataFrame, *, min_n: int = 30
) -> tuple[pd.Series, dict[str, int]]:
    """Pool small-N sectors into ``'Other'`` and report N-per-sector (D5-10, P7).

    Sectors with fewer than ``min_n`` IPOs (and any missing/NaN sector) are mapped
    to a pooled ``'Other'`` bucket so a 4-IPO sector never becomes a leak-prone
    single-value slice. The returned ``n_per_sector`` report carries the ORIGINAL
    per-sector counts so the thinness stays visible (never hidden by the pooling).

    Args:
        panel: a panel carrying a ``sector`` column (e.g. ``CatalogueIPO.sector``).
        min_n: the pooling threshold (guideline ~30, D5-10).

    Returns:
        ``(pooled_sector, n_per_sector)``:
          - ``pooled_sector`` — the ``sector`` Series with rare / missing sectors
            mapped to ``'Other'`` (the value that feeds sector features/baselines).
          - ``n_per_sector`` — ``{sector: original_count}`` for every non-null
            sector label (thinness report).

    Raises:
        ValueError: if the panel has no ``sector`` column.
    """
    if "sector" not in panel.columns:
        raise ValueError(
            "pool_sectors needs a 'sector' column to pool small-N sectors (D5-10)."
        )

    sectors = panel["sector"]
    counts = sectors.value_counts(dropna=True)
    n_per_sector = {str(label): int(count) for label, count in counts.items()}
    keep = {label for label, count in counts.items() if count >= min_n}

    def _pool(value: Any) -> str:
        if pd.isna(value):
            return "Other"
        return value if value in keep else "Other"

    pooled = sectors.map(_pool)
    return pooled, n_per_sector


__all__ = [
    "LeakageError",
    "SNAPSHOTS_DIR",
    "REDFLAG_DIR",
    "build_features",
    "leakage_audit",
    "anchor_leakage_audit",
    "pool_sectors",
]
