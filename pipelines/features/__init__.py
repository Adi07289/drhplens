"""
pipelines/features/ — Leakage-gated feature layer for the listing-day forecaster.

This package turns the survivorship-corrected historical panel
(``pipelines.historical``) into the model's design matrix ``X``, behind a hard
``available_at <= T0`` leakage gate. It is the primary P4/lookahead defense for
the walk-forward model in 05-05, and it emits a leakage audit for the model card
(FCAST-02 / D5-01 / D5-08).

T0 (the leakage boundary)
-------------------------
``T0`` is the **issue-open day** — ``issue_date`` in the panel. D5-01 fixes the
cutoff at T0 issue-open ("pre-apply"): every feature must be knowable at or before
issue open. This **supersedes** FCAST-02's literal "T−1 of listing" wording; the
ROADMAP SC-5 T0-issue-open definition is canonical (note the reconciliation).
A feature whose ``available_at`` resolves *after* T0 is look-ahead leakage and the
builder RAISES (see ``build.build_features`` / ``build.LeakageError``).

Thin slice (D5-06a — issue-structure only)
------------------------------------------
This module owns **only** family (a) of RESEARCH §Pattern 3: the issue-structure
features, every one of which is disclosed in the DRHP/RHP by its filing date and
is therefore ``available_at <= T0`` by construction:

  * ``issue_size_cr``          — total issue size, ₹ crore
  * ``price_band_width_pct``   — (band_high − band_low) / band_low, %
  * ``ofs_fraction``           — offer-for-sale share of the issue (0..1)
  * ``promoter_dilution_pct``  — promoter holding reduction at the issue, %
  * ``lot_size``               — bid-lot size / minimum-investment proxy

Regime (b), DRHP-derived (c) and anchor-demand (d) feature families are
DELIBERATELY DEFERRED to 05-08 (D5-05 verified-subset-first) so the end-to-end
model chain can land first. Do NOT add them here.

Honesty invariants
-------------------
* **Replace-with-NaN.** A missing issue-structure value is retained as ``NaN`` and
  counted — never fabricated as 0. Row count is preserved (mirrors
  ``pipelines.historical.assemble_panel``). ``lot_size`` is therefore ``float64``
  (not ``int64``) so a missing lot size survives as NaN.
* **Excluded by construction.** GMP and final / at-close subscription multiples
  can NEVER be features (FCAST-02 / compliance / circularity). They are named in
  ``EXCLUDED_FROM_MODEL`` and the builder asserts none of them is ever a built
  column.

This ``__init__`` owns the **feature contract** (mirroring
``pipelines/historical/__init__.py``'s column-contract-as-constant grammar):
  - ``FEATURE_SPECS``        — ordered ``name -> (dtype, available_at_rule)``.
  - ``FEATURE_COLUMNS``      — the ordered feature names (like ``PANEL_COLUMNS``).
  - ``FEATURE_DTYPES``       — dtypes chosen so NaN survives (all float64).
  - ``EXCLUDED_FROM_MODEL``  — the never-a-feature sentinel (GMP / subscription).
  - ``AVAILABLE_AT_FILING``  — the family-(a) available_at rule token.

``build.py`` (the feature-matrix assembler + leakage gate + audit) imports this
contract. Keep it declaration-only — no pandas frame building here.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# T0 — the leakage boundary (D5-01)
# ---------------------------------------------------------------------------
# T0 is the issue-open day, i.e. the panel's ``issue_date``. Every feature must be
# knowable at or before T0. This supersedes FCAST-02's literal "T−1 of listing"
# wording (ROADMAP SC-5 T0-issue-open is canonical — reconciliation noted).
T0_COLUMN: str = "issue_date"
T0_RULE: str = (
    "T0 = issue-open day (the panel's issue_date). Every issue-structure feature's "
    "available_at is the DRHP/RHP filing date, which is <= T0 by construction "
    "(D5-01 supersedes FCAST-02's literal 'T-1 of listing' wording)."
)

# ---------------------------------------------------------------------------
# available_at rule tokens (RESEARCH §Pattern 3 family column)
# ---------------------------------------------------------------------------
# Family (a) issue-structure features are all disclosed at the DRHP/RHP filing
# date, which is on or before issue open (<= T0). This is the ONLY rule this thin
# slice uses; the regime / anchor rule tokens (T0-1 EOD snapshot, pre-open anchor
# allocation) land with families (b)/(d) in 05-08.
AVAILABLE_AT_FILING: str = "filing_date"

# ---------------------------------------------------------------------------
# Feature contract (issue-structure only, D5-06a) — declaration only
# ---------------------------------------------------------------------------
# Ordered mapping: feature name -> (dtype, available_at rule). Mirrors the
# PANEL_COLUMNS/PANEL_DTYPES/STATUS_VALUES contract grammar in
# pipelines/historical/__init__.py. dtypes are all float64 so a missing value is
# NaN-retained (replace-with-NaN honesty) — including lot_size (int would swallow
# the NaN and fabricate a value).
FEATURE_SPECS: dict[str, tuple[str, str]] = {
    "issue_size_cr": ("float64", AVAILABLE_AT_FILING),
    "price_band_width_pct": ("float64", AVAILABLE_AT_FILING),
    "ofs_fraction": ("float64", AVAILABLE_AT_FILING),
    "promoter_dilution_pct": ("float64", AVAILABLE_AT_FILING),
    "lot_size": ("float64", AVAILABLE_AT_FILING),
}

# The ordered feature names (the analog of PANEL_COLUMNS).
FEATURE_COLUMNS: tuple[str, ...] = tuple(FEATURE_SPECS.keys())

# dtypes chosen so NaN survives (the analog of PANEL_DTYPES).
FEATURE_DTYPES: dict[str, str] = {
    name: dtype for name, (dtype, _rule) in FEATURE_SPECS.items()
}

# Per-feature available_at rule (the analog of STATUS_VALUES — the leakage-gate
# contract surface). Every issue-structure feature is filing-date-anchored (<= T0).
FEATURE_AVAILABLE_AT: dict[str, str] = {
    name: rule for name, (_dtype, rule) in FEATURE_SPECS.items()
}

# ---------------------------------------------------------------------------
# Never-a-feature sentinel (FCAST-02 exclusion invariant, T-05-04-EXCL)
# ---------------------------------------------------------------------------
# GMP and final/at-close subscription multiples (and any listing-day price) are
# EXCLUDED BY CONSTRUCTION: they are either post-T0 (subscription closes after
# issue open; listing-day price is the target) or compliance-barred/circular (GMP).
# The builder asserts none of these tokens is ever a built column.
EXCLUDED_FROM_MODEL: frozenset[str] = frozenset(
    {
        "gmp",                    # grey-market premium — compliance-barred + circular
        "subscription_at_close",  # final subscription multiple — closes AFTER T0
        "qib",                    # at-close QIB subscription multiple — post-T0
        "nii",                    # at-close NII subscription multiple — post-T0
        "rii",                    # at-close retail subscription multiple — post-T0
        "listing_day_close",      # the listing-day price — post-T0 (target input)
        "listing_day_return",     # the target itself — never a feature
    }
)

# Substring tokens the builder forbids in any built column name (catches
# subscription_pct, gmp_premium, etc. even if not spelled exactly as above).
EXCLUDED_SUBSTRINGS: tuple[str, ...] = ("gmp", "subscri", "listing_day")


__all__ = [
    "T0_COLUMN",
    "T0_RULE",
    "AVAILABLE_AT_FILING",
    "FEATURE_SPECS",
    "FEATURE_COLUMNS",
    "FEATURE_DTYPES",
    "FEATURE_AVAILABLE_AT",
    "EXCLUDED_FROM_MODEL",
    "EXCLUDED_SUBSTRINGS",
]
