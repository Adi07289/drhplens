"""
scripts/eval_extraction.py — EXTRACT-03 per-field-type extraction F1 scorer.

The committed, honest, per-field-type F1 story for the 7-field red-flag table
(D3-07). Mirrors scripts/run_eval.py's harness skeleton (project-root-on-path,
jsonl loader, dated-markdown writer to eval/reports/) but scores STRUCTURED
extractions, not free-text answers:

  - numeric fields (rpt_pct, ofs_vs_fresh, promoter_pledge_pct, debt_trajectory):
    abs(pred - gold) <= agent.policies.F1_NUMERIC_TOLERANCES[field] (no hard-coded
    tolerance in this file — the per-field tolerances live in policies).
  - boolean field (going_concern): exact equality, no tolerance.
  - set fields (customer_concentration, auditor_history): rapidfuzz set-overlap
    precision/recall F1 (token_set_ratio >= thresh).

Refusals are FIRST-CLASS labels (D3-03): a gold cell labeled not_disclosed where
the extractor stored a RefusalResponse scores CORRECT and is NEVER dropped from
the F1 denominator — dropping refusals would let an extractor inflate F1 by simply
refusing on hard fields (P10 / evaluation-theater antibody).

The scorer is OFFLINE: it reads predictions from the cached
data/redflag/<drhp_id>.json via pipelines.redflag.load_redflag (the allow-list-
gated read path, T-03-01) — it never invokes the agent graph, Qdrant, or Gemini.
Each prediction carries its confidence_tier, so the report splits per-field F1
AND accuracy by confidence bucket (high/med/low, D3-04). Every metric is followed
by an interpretation paragraph (P10 — "what does this F1 miss?").

Usage:
    python scripts/eval_extraction.py
    python scripts/eval_extraction.py --labels eval/gold/extraction_labels.jsonl
    python scripts/eval_extraction.py --output-dir eval/reports
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# Ensure project root on path (mirrors run_eval.py:31-32)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.policies import F1_NUMERIC_TOLERANCES  # noqa: E402
from agent.redflag_schema import REDFLAG_FIELD_KEYS  # noqa: E402
from agent.schemas import RefusalResponse  # noqa: E402

# rapidfuzz set-overlap match threshold (mirrors the cite-check fuzzy posture).
SET_OVERLAP_THRESHOLD: int = 85


# ===========================================================================
# Per-field-type match primitives (the scorer logic — unit-tested offline)
# ===========================================================================


def numeric_match(pred: float, gold: float, tol: float) -> bool:
    """True iff a numeric prediction is within an absolute tolerance of gold."""
    return abs(float(pred) - float(gold)) <= tol


def boolean_match(pred: bool, gold: bool) -> bool:
    """True iff a boolean prediction exactly equals gold (no tolerance)."""
    return bool(pred) == bool(gold)


def set_overlap_f1(pred: list[str], gold: list[str], thresh: int = SET_OVERLAP_THRESHOLD) -> float:
    """Item-level precision/recall F1 via rapidfuzz token_set_ratio.

    A gold item is "matched" when some predicted item scores
    token_set_ratio >= thresh against it (fuzzy item agreement). Empty pred AND
    empty gold returns 1.0 (correctly-empty agreement); a disjoint pred/gold
    returns 0.0.
    """
    pred = list(pred or [])
    gold = list(gold or [])
    if not pred and not gold:
        return 1.0
    matched_gold = sum(
        1 for g in gold if any(fuzz.token_set_ratio(g, p) >= thresh for p in pred)
    )
    matched_pred = sum(
        1 for p in pred if any(fuzz.token_set_ratio(p, g) >= thresh for g in gold)
    )
    prec = matched_pred / len(pred) if pred else 0.0
    rec = matched_gold / len(gold) if gold else 0.0
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def refusal_matches_absence(gold_value: Any, prediction: Any) -> bool:
    """True iff a not_disclosed gold cell is matched by a stored refusal (D3-03).

    A gold cell is "absent" when gold_value is None or the literal
    "not_disclosed". It is CORRECT exactly when the prediction is a
    RefusalResponse (the extractor honestly refused). A refusal against a
    DISCLOSED gold is incorrect (the extractor wrongly refused). A non-refusal
    against an absent gold is incorrect. The cell is never dropped either way.
    """
    gold_absent = gold_value is None or gold_value == "not_disclosed"
    pred_is_refusal = isinstance(prediction, RefusalResponse)
    # Correct only when the gold is absent AND the extractor honestly refused.
    # A refusal against a disclosed gold (or a value against an absent gold) is
    # a miss, but the cell is never dropped from the denominator (D3-03).
    return gold_absent and pred_is_refusal


def score_field(row: dict, prediction: Any) -> float:
    """Score one (gold-row, prediction) pair to a [0.0, 1.0] field score.

    Dispatches on the gold row's field_type. A not_disclosed gold cell is scored
    by refusal_matches_absence (refusal -> 1.0, anything else -> 0.0) and is kept
    in the denominator (D3-03). A disclosed gold uses the per-type rule:
    numeric tolerance (F1_NUMERIC_TOLERANCES[field]) / boolean exact / set-overlap.
    """
    gold_value = row.get("gold_value")
    field_type = row["field_type"]

    # First-class absence: not_disclosed gold is scored by refusal-match, never
    # dropped from the denominator.
    if gold_value is None or gold_value == "not_disclosed":
        return 1.0 if refusal_matches_absence(gold_value, prediction) else 0.0

    # A refusal where gold IS disclosed is a miss (extractor wrongly refused).
    if isinstance(prediction, RefusalResponse):
        return 0.0

    if field_type == "numeric":
        tol = F1_NUMERIC_TOLERANCES[row["field_key"]]
        return 1.0 if numeric_match(prediction, gold_value, tol) else 0.0
    if field_type == "boolean":
        return 1.0 if boolean_match(prediction, gold_value) else 0.0
    if field_type == "set":
        pred_list = prediction if isinstance(prediction, list) else [prediction]
        return set_overlap_f1(pred_list, gold_value)
    raise ValueError(f"Unknown field_type {field_type!r} for field {row.get('field_key')!r}")


def bucket_split(scored_rows: list[dict]) -> dict[str, dict[str, float]]:
    """Split scored rows by confidence bucket (D3-04), preserving not_disclosed.

    Each scored row carries {confidence_bucket, score}. Returns
    {bucket -> {"n", "mean_score"}}. A row whose confidence_bucket is None
    (a not-disclosed field carries no tier, D3-03) lands in its own
    "not_disclosed" group — never silently merged into high/med/low or dropped.
    """
    groups: dict[str, list[float]] = {}
    for r in scored_rows:
        bucket = r.get("confidence_bucket")
        key = bucket if bucket in ("high", "medium", "low") else "not_disclosed"
        groups.setdefault(key, []).append(float(r["score"]))
    return {
        bucket: {
            "n": len(scores),
            "mean_score": sum(scores) / len(scores) if scores else 0.0,
        }
        for bucket, scores in groups.items()
    }


# ===========================================================================
# Offline prediction extraction from the cached red-flag record
# ===========================================================================


def _prediction_for_field(record: Any, field_key: str) -> Any:
    """Pull one field's prediction from a cached RedFlagRecord (offline).

    Returns a RefusalResponse (not-disclosed/blocked field), or a parsed
    predicted value for a GroundedAnswer field, or None if the record has no
    such field. The GroundedAnswer -> value parse is intentionally lightweight:
    the scorer's job is to score the EXTRACTED structured value; a richer parser
    is the natural live-run extension (documented as deferred).
    """
    field = record.fields.get(field_key)
    if field is None:
        return None
    value = field.value
    if isinstance(value, RefusalResponse):
        return value
    # GroundedAnswer: the structured value parse from answer_prose/claims is a
    # live-run concern (no cached records exist offline today). Return the raw
    # GroundedAnswer; score_field treats a non-refusal, non-typed value via its
    # type branch when a real parsed value is supplied at live-run time.
    return value


def _load_labels(labels_path: Path) -> list[dict]:
    """Load the gold labels jsonl (one JSON object per line), mirror run_eval."""
    rows = [
        json.loads(line)
        for line in labels_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    unknown = {r["field_key"] for r in rows} - set(REDFLAG_FIELD_KEYS)
    if unknown:
        raise ValueError(f"Unknown field_key(s) in gold labels: {sorted(unknown)}")
    return rows


# ===========================================================================
# Report writer (dated markdown -> eval/reports/, mirrors run_eval.py:244-305)
# ===========================================================================


def _write_report(
    per_field: list[dict],
    buckets: dict[str, dict[str, float]],
    n_labels: int,
    output_dir: str,
) -> Path:
    """Write the dated per-field-F1 + confidence-bucket markdown report."""
    out_dir = PROJECT_ROOT / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{date.today()}-extraction-f1.md"

    scored = [r for r in per_field if r.get("score") is not None]
    macro_f1 = sum(r["score"] for r in scored) / len(scored) if scored else 0.0

    lines = [
        f"# Red-Flag Extraction F1 — {date.today()}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Labeled cells (honest n) | {n_labels} |",
        f"| Scored cells | {len(scored)} |",
        f"| Macro F1 (mean per-field score) | {macro_f1:.3f} |",
        "",
        "**Interpretation (P10):** Macro F1 is the unweighted mean of the "
        "per-field scores below — numeric fields scored within their committed "
        "absolute tolerance, going-concern scored on exact equality, and the set "
        "fields scored by item-level rapidfuzz overlap. It says nothing about "
        "*which* fields fail: a high macro F1 can hide a single systematically-"
        "wrong field, so read the per-field table, not just this number. Refusals "
        "on not_disclosed cells count toward F1 and are NOT dropped (D3-03).",
        "",
        "## Per-Field F1",
        "",
        "| field_key | field_type | gold | prediction | score |",
        "|---|---|---|---|---|",
    ]
    for r in per_field:
        score_str = f"{r['score']:.2f}" if r.get("score") is not None else "—"
        lines.append(
            f"| {r['field_key']} | {r['field_type']} | {r['gold_repr']} | "
            f"{r['pred_repr']} | {score_str} |"
        )

    lines += [
        "",
        "**Interpretation (P10):** A numeric field's score is binary (1.0 inside "
        "its `F1_NUMERIC_TOLERANCES` band, 0.0 outside) — it does not reward "
        "near-misses, so a field printing 'approximately' figures is scored "
        "generously by the ±tolerance, not the digits. A set field's score is the "
        "harmonic mean of item precision and recall, so a prediction that adds "
        "spurious customers is penalized as hard as one that omits real ones. A "
        "not_disclosed cell scores 1.0 ONLY when the extractor honestly refuses — "
        "a fabricated value on an absent field scores 0.0.",
        "",
        "## Confidence-Bucket Reliability (D3-04)",
        "",
        "| confidence_bucket | n | mean_score |",
        "|---|---|---|",
    ]
    for bucket in ("high", "medium", "low", "not_disclosed"):
        if bucket in buckets:
            b = buckets[bucket]
            lines.append(f"| {bucket} | {b['n']} | {b['mean_score']:.2f} |")

    lines += [
        "",
        "**Interpretation (P10):** This table is the confidence-reliability "
        "check — if the `high` bucket does not score meaningfully better than "
        "`low`, the confidence tier is decoration, not signal (evaluation "
        "theater). A well-calibrated extractor has monotonically decreasing "
        "mean_score from high -> low. The `not_disclosed` bucket carries fields "
        "the DRHP does not disclose; its mean_score measures honest-refusal "
        "accuracy, kept first-class and never folded into the graded buckets.",
        "",
        "## Notes",
        "",
        "- Gold set: `eval/gold/extraction_labels.jsonl` (swiggy-anchored; honest "
        "n per D3-05). Labeling protocol: `eval/gold/extraction_rubric.md`.",
        "- Scorer is OFFLINE: predictions read from cached "
        "`data/redflag/<id>.json` via `load_redflag`; no live Qdrant/Gemini call.",
        "- Per-field numeric tolerances from `agent.policies.F1_NUMERIC_TOLERANCES`; "
        "set overlap via rapidfuzz (stdlib + vendored rapidfuzz only; "
        "no TF-IDF / ML-library dependency).",
        f"- Generated: {date.today()} by scripts/eval_extraction.py.",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ===========================================================================
# Main scorer (offline; reads cached records via load_redflag)
# ===========================================================================


def run_extraction_f1(
    labels_path: str = "eval/gold/extraction_labels.jsonl",
    output_dir: str = "eval/reports",
    write_report: bool = True,
) -> dict[str, Any]:
    """Score the gold labels against cached predictions and write the report.

    Reads predictions OFFLINE from data/redflag/<drhp_id>.json via load_redflag
    (allow-list gated, T-03-01). When no cached record exists for a labeled
    drhp_id, the per-field score is left unscored ("—") — the run still emits the
    report skeleton so the methodology pane has a committed artifact (the real
    end-to-end run over cached records is deferred-to-live, like 03-03's
    precompute).
    """
    from pipelines.redflag import load_redflag  # offline cache reader

    labels_file = PROJECT_ROOT / labels_path
    if not labels_file.exists():
        print(f"ERROR: gold labels not found at {labels_file}")
        sys.exit(1)

    rows = _load_labels(labels_file)
    print(f"Loaded {len(rows)} gold labels from {labels_file}")

    # Cache the loaded record per drhp_id (offline read; missing cache tolerated).
    record_cache: dict[str, Any] = {}
    per_field: list[dict] = []
    scored_rows: list[dict] = []

    for row in rows:
        drhp_id = row["drhp_id"]
        field_key = row["field_key"]
        gold_value = row.get("gold_value")
        gold_absent = gold_value is None or gold_value == "not_disclosed"

        if drhp_id not in record_cache:
            try:
                record_cache[drhp_id] = load_redflag(drhp_id)
            except (FileNotFoundError, ValueError) as exc:
                record_cache[drhp_id] = None
                print(f"  [{drhp_id}] no cached record ({type(exc).__name__}); "
                      f"fields left unscored (deferred-to-live)")

        record = record_cache[drhp_id]
        prediction = (
            _prediction_for_field(record, field_key) if record is not None else None
        )

        # Confidence bucket comes from the cached field's tier; a not-disclosed
        # field carries no tier (None) -> the not_disclosed bucket (D3-03).
        confidence_bucket = None
        if record is not None and field_key in record.fields:
            confidence_bucket = record.fields[field_key].confidence_tier

        score: float | None
        if record is None or (prediction is None and not gold_absent):
            score = None  # no cached prediction -> unscored (deferred-to-live)
        else:
            score = score_field(row, prediction)
            scored_rows.append(
                {"confidence_bucket": confidence_bucket, "score": score}
            )

        per_field.append(
            {
                "drhp_id": drhp_id,
                "field_key": field_key,
                "field_type": row["field_type"],
                "gold_repr": "not_disclosed" if gold_absent else str(gold_value),
                "pred_repr": (
                    "refusal"
                    if isinstance(prediction, RefusalResponse)
                    else ("—" if prediction is None else "value")
                ),
                "score": score,
            }
        )

    buckets = bucket_split(scored_rows)

    report_path = None
    if write_report:
        report_path = _write_report(per_field, buckets, len(rows), output_dir)
        print(f"Report written to: {report_path}")

    return {
        "per_field": per_field,
        "buckets": buckets,
        "report_path": report_path,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DRHPLens red-flag extraction F1 scorer")
    parser.add_argument("--labels", default="eval/gold/extraction_labels.jsonl")
    parser.add_argument("--output-dir", default="eval/reports")
    args = parser.parse_args()
    run_extraction_f1(labels_path=args.labels, output_dir=args.output_dir)
