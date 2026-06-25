"""
pipelines/risk_idf.py — In-corpus IDF risk specificity ranker (D3-14 / P12).

THE only genuinely-new algorithm in Phase 3 (everything else extends existing,
tested code). A ~40-line stdlib in-corpus IDF ranker with a hand-curated
boilerplate floor that foregrounds issuer-specific risks over generic
merchant-banker boilerplate (ROADMAP success criterion 5).

Algorithm (RESEARCH Pattern 4):
  1. Normalize every risk statement with cite_check._normalize (the ONE shared
     normalizer — no second normalizer is written here).
  2. Tokenize into 3-5 word PHRASE-LEVEL shingles. Boilerplate is phrasal, not
     unigram (RESEARCH Pitfall 2) — a 4-word generic phrase recurs across DRHPs
     even when its individual words do not.
  3. df(shingle) = number of corpus risk sections containing the shingle;
     idf(shingle) = log(N / (1 + df)) over the N-document corpus. A shingle
     absent from the corpus has df=0 -> idf=log(N) (the maximum), correctly
     rewarding issuer-unique phrasing.
  4. A risk's specificity score = the MEAN IDF of its shingles (falling back to
     the single shingle / the max when a statement is too short to shingle).
  5. Boilerplate floor: if a normalized risk's rapidfuzz token_set_ratio against
     ANY phrase in eval/gold/boilerplate_phrases.txt is
     >= IDF_BOILERPLATE_FUZZ_THRESHOLD, clamp its band to industry_standard
     regardless of IDF — a deterministic guard against small-n IDF noise.
  6. Map score -> a neutral specificity band via IDF_BAND_THRESHOLDS.

Corpus scope: data/catalogue_loader.load_catalogue() supplies the n≈8 ingested
DRHPs (D3-05). N is SMALL — IDF is noisy at this scale (documented honestly,
A1/D3-14); the boilerplate floor de-risks the small-n regime.

Neutrality (L3-1): the output is a NEUTRAL ordered list — a specificity indicator
only. NO red/green, NO verdict, NO "good"/"bad" field. The product describes how
issuer-specific a risk is; it never judges whether the risk is dangerous.

Deterministic + offline: stdlib math.log + collections.Counter + the already-
vendored rapidfuzz + cite_check._normalize. No TF-IDF library dependency
(RESEARCH anti-pattern — the IDF is hand-rolled stdlib), NO LLM, NO network.
"""
from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from agent.nodes.cite_check import _normalize
from agent.policies import IDF_BAND_THRESHOLDS, IDF_BOILERPLATE_FUZZ_THRESHOLD
from agent.redflag_schema import RankedRisk

# Phrase-level shingle width (RESEARCH Pattern 4 step 2: 3-5 word n-grams).
_SHINGLE_MIN = 3
_SHINGLE_MAX = 5

DEFAULT_BOILERPLATE_PATH: Path = (
    Path(__file__).parent.parent / "eval" / "gold" / "boilerplate_phrases.txt"
)


def _shingles(normalized: str) -> list[str]:
    """Build 3-5 word phrase shingles from a normalized risk statement.

    A statement shorter than _SHINGLE_MIN words yields a single whole-statement
    shingle so very short risks still get an IDF score.
    """
    words = normalized.split()
    if not words:
        return []
    if len(words) < _SHINGLE_MIN:
        return [" ".join(words)]
    shingles: list[str] = []
    for width in range(_SHINGLE_MIN, _SHINGLE_MAX + 1):
        for i in range(len(words) - width + 1):
            shingles.append(" ".join(words[i : i + width]))
    return shingles


def _build_corpus_df(corpus_sections: list[str]) -> tuple[Counter, int]:
    """Document-frequency Counter over the corpus + the corpus size N.

    df(shingle) = number of DISTINCT corpus sections the shingle appears in.
    """
    df: Counter = Counter()
    for section in corpus_sections:
        section_shingles = set(_shingles(_normalize(section)))
        for shingle in section_shingles:
            df[shingle] += 1
    return df, len(corpus_sections)


def _idf(shingle: str, df: Counter, n: int) -> float:
    """idf = log(N / (1 + df)). A corpus-absent shingle (df=0) -> log(N) (max)."""
    return math.log(n / (1 + df.get(shingle, 0)))


def _score_risk(normalized: str, df: Counter, n: int) -> float:
    """A risk's specificity score = mean IDF of its shingles (higher = unique)."""
    shingles = _shingles(normalized)
    if not shingles:
        return 0.0
    return sum(_idf(s, df, n) for s in shingles) / len(shingles)


def _load_boilerplate_phrases(path: Path) -> list[str]:
    """Read the hand-curated floor list (one normalized phrase per non-# line)."""
    if not path.exists():
        return []
    phrases: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        phrases.append(_normalize(stripped))
    return phrases


def _is_boilerplate(normalized: str, boilerplate_phrases: list[str]) -> bool:
    """True iff the risk fuzzy-matches any floor phrase at/above the threshold."""
    return any(
        fuzz.token_set_ratio(normalized, phrase) >= IDF_BOILERPLATE_FUZZ_THRESHOLD
        for phrase in boilerplate_phrases
    )


def _band(score: float) -> str:
    """Map an IDF score to a neutral specificity band via IDF_BAND_THRESHOLDS."""
    low, high = IDF_BAND_THRESHOLDS
    if score >= high:
        return "issuer_specific"
    if score >= low:
        return "mostly_issuer_specific"
    return "industry_standard"


def rank_risks(
    risk_claims: list[tuple[str, str]],
    corpus_risk_sections: list[str] | None = None,
    *,
    boilerplate_path: Path | None = None,
) -> list[RankedRisk]:
    """Rank risk claims by in-corpus IDF specificity with a boilerplate floor.

    Args:
        risk_claims: list of (claim_id, risk_statement) pairs to rank.
        corpus_risk_sections: the n≈8 risk-section corpus the IDF is computed
            over. If None, the corpus is built from load_catalogue()'s ingested
            DRHP risk sections (right-sized to actually-ingested docs, D3-05).
        boilerplate_path: override the hand-curated floor list path (tests).

    Returns:
        A NEUTRAL list[RankedRisk] ordered by DESCENDING idf_score, each carrying
        its source claim_id and a specificity_band (issuer_specific /
        mostly_issuer_specific / industry_standard). A risk matching the
        boilerplate floor is clamped to industry_standard regardless of IDF.
    """
    if corpus_risk_sections is None:
        corpus_risk_sections = _corpus_from_catalogue()

    boilerplate_phrases = _load_boilerplate_phrases(
        boilerplate_path or DEFAULT_BOILERPLATE_PATH
    )

    # Guard against an empty corpus (n=0 would make log undefined): treat as
    # max-specificity-neutral by scoring 0 and letting the floor do the work.
    n = len(corpus_risk_sections)
    df: Counter = Counter()
    if n > 0:
        df, n = _build_corpus_df(corpus_risk_sections)

    ranked: list[RankedRisk] = []
    for claim_id, statement in risk_claims:
        normalized = _normalize(statement)
        score = _score_risk(normalized, df, n) if n > 0 else 0.0
        if _is_boilerplate(normalized, boilerplate_phrases):
            band = "industry_standard"
        else:
            band = _band(score)
        ranked.append(
            RankedRisk(
                claim_id=claim_id,
                idf_score=round(score, 4),
                specificity_band=band,  # type: ignore[arg-type]
            )
        )

    ranked.sort(key=lambda r: r.idf_score, reverse=True)
    return ranked


def _corpus_from_catalogue() -> list[str]:
    """Build the IDF corpus from the ingested DRHP snapshot risk sections.

    Right-sizes N to actually-ingested DRHPs (D3-05): for each catalogue IPO that
    has a snapshot cache with a grounded "risks" field, the risk prose is one
    corpus document. IPOs without a snapshot contribute nothing (honest small-n).
    """
    from agent.schemas import GroundedAnswer
    from data.catalogue_loader import load_catalogue
    from pipelines.snapshot import load_snapshot

    sections: list[str] = []
    for ipo in load_catalogue():
        try:
            snap = load_snapshot(ipo.drhp_id)
        except FileNotFoundError:
            continue
        risks = snap.fields.get("risks")
        if isinstance(risks, GroundedAnswer):
            sections.append(risks.answer_prose)
    return sections
