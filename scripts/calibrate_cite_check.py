"""
scripts/calibrate_cite_check.py — data-driven calibration of CITE_CHECK_TOKEN_RATIO.

The cite-check honesty gate (agent/nodes/cite_check.py) accepts a claim as grounded when

    fuzz.token_set_ratio(normalize(claim), normalize(source_window)) >= CITE_CHECK_TOKEN_RATIO

Too high a threshold (the original 80) rejected even a strong model's legitimately
grounded, naturally-paraphrased claims; too low admits off-topic claims. This script
chooses the threshold from a small LABELED set of (claim, source, label) pairs so the
value is picked with evidence, not by feel. It is the reproducible calibration artifact
behind the CITE_CHECK_TOKEN_RATIO value in agent/policies.py.

Run: .venv/bin/python scripts/calibrate_cite_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rapidfuzz import fuzz  # noqa: E402

from agent.nodes.cite_check import _normalize  # noqa: E402 - reuse the gate's exact normalizer

# Labeled calibration set. grounded = a faithful paraphrase of the source (the way an LLM
# writes a cited claim — shares meaning, reworded); hallucinated = a plausible but
# unsupported claim about content ABSENT from the source. Sources are DRHP-style
# risk/financial passages (the Swiggy domain).
CASES: list[tuple[str, str, str]] = [
    ("grounded",
     "Any security breach or data incident affecting the company or its vendors could result in liability, regulatory fines, and loss of user trust.",
     "Any actual or perceived breach of our security measures or those of our third-party vendors could result in significant liabilities, regulatory penalties, reputational harm and a loss of confidence among our users."),
    ("grounded",
     "The company depends on preserving its brand and reputation to attract and retain users.",
     "Maintaining and enhancing the Swiggy brand and our reputation is critical to our ability to attract new users, retain existing users, and grow our business."),
    ("grounded",
     "The business relies on its ability to recruit and retain skilled delivery partners and employees.",
     "Our success depends on our ability to attract, recruit, retain and effectively manage delivery partners and skilled employees across our operations."),
    ("grounded",
     "The company has incurred net losses historically and may not achieve profitability.",
     "We have a history of net losses and we may not be able to achieve or sustain profitability in the future."),
    ("grounded",
     "Changes to food-delivery regulation or gig-worker classification could adversely affect operations.",
     "Changes in laws or regulations relating to the food delivery industry, or the classification of gig workers, could materially and adversely affect our business and results of operations."),
    ("grounded",
     "A significant portion of orders is concentrated in a few metropolitan markets, exposing the company to regional risk.",
     "A substantial portion of our order volume is concentrated in a limited number of metropolitan cities, and any adverse developments in these markets could disproportionately affect our results."),
    ("hallucinated",
     "The company's revenue grew by 50% year over year, driven by international expansion into Europe.",
     "Any actual or perceived breach of our security measures or those of our third-party vendors could result in significant liabilities, regulatory penalties, reputational harm and a loss of confidence among our users."),
    ("hallucinated",
     "The promoters have pledged 30% of their shareholding to secure a term loan from a foreign bank.",
     "Maintaining and enhancing the Swiggy brand and our reputation is critical to our ability to attract new users, retain existing users, and grow our business."),
    ("hallucinated",
     "The company operates 200 dark stores and plans to double the count within a year.",
     "We have a history of net losses and we may not be able to achieve or sustain profitability in the future."),
    ("hallucinated",
     "A dividend of 15% was declared for the most recent financial year.",
     "Changes in laws or regulations relating to the food delivery industry, or the classification of gig workers, could materially and adversely affect our business and results of operations."),
    ("hallucinated",
     "The founder previously served as the chief executive of a large telecom operator.",
     "Our success depends on our ability to attract, recruit, retain and effectively manage delivery partners and skilled employees across our operations."),
    ("hallucinated",
     "The company holds patents on its logistics algorithm across 12 countries.",
     "A substantial portion of our order volume is concentrated in a limited number of metropolitan cities, and any adverse developments in these markets could disproportionately affect our results."),
]


def main() -> None:
    grounded: list[float] = []
    hall: list[float] = []
    print("per-case token_set_ratio (claim vs source):")
    for label, claim, source in CASES:
        r = fuzz.token_set_ratio(_normalize(claim), _normalize(source))
        (grounded if label == "grounded" else hall).append(r)
        print(f"  {label:12s} ratio={r:6.2f}  {claim[:58]}")

    gmin, gmax = min(grounded), max(grounded)
    hmin, hmax = min(hall), max(hall)
    print(f"\ngrounded     (n={len(grounded)}): min={gmin:.1f} max={gmax:.1f}")
    print(f"hallucinated (n={len(hall)}): min={hmin:.1f} max={hmax:.1f}")

    if gmin > hmax:
        rec = int((gmin + hmax) // 2)  # midpoint of the clean separating gap
        print(
            f"\nSeparable — gap ({hmax:.0f}, {gmin:.0f}). "
            f"Recommended CITE_CHECK_TOKEN_RATIO = {rec} "
            f"(midpoint: max recall of grounded, still above every hallucination)."
        )
    else:
        # Overlap: pick the threshold that maximizes balanced accuracy.
        best_t, best_acc = 0, -1.0
        for t in range(0, 101):
            tp = sum(1 for r in grounded if r >= t)
            tn = sum(1 for r in hall if r < t)
            acc = (tp / len(grounded) + tn / len(hall)) / 2
            if acc > best_acc:
                best_acc, best_t = acc, t
        print(
            f"\nOverlap (grounded min {gmin:.1f} <= hallucinated max {hmax:.1f}). "
            f"Recommended CITE_CHECK_TOKEN_RATIO = {best_t} "
            f"(balanced accuracy {best_acc:.0%})."
        )


if __name__ == "__main__":
    main()
