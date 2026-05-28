r"""
Deterministic banned-token scrubber for DRHPLens.

TRUST-02 anchor: blocks all banned-token conjugations (via the \\w* morphological
suffix in BANNED_TOKEN_PATTERN) before LLM output reaches the user.

Design choices (locked — document here; changing any is a Phase-protocol discussion):

1. PURE DETERMINISTIC REGEX — no LLM call, no stochastic logic.
   Per PITFALL 5 prevention and ASVS V11 "deterministic business logic control":
   the scrubber's result is reproducible given the same input string, always.

2. NFKC NORMALIZATION before matching.
   Unicode homoglyphs (e.g. "ѕubscribe" with cyrillic 's') are NOT normalized
   by NFKC to 'subscribe', so a homoglyph attack does NOT fire the scrubber.
   This is the documented behavior: we do not try to defeat homoglyph attacks
   because the attack surface is the LLM output (which uses Latin characters),
   not adversarial user input.

3. HARD-BLOCK-AND-REGENERATE semantics (D-09 locked default).
   The scrubber returns ScrubResult and the Wave 3 graph node reads it.
   If scrub_result.passed is False AND regenerate_attempts < 1: retry generate.
   If scrub_result.passed is False AND regenerate_attempts >= 1: refuse.
   The scrubber itself has NO knowledge of the retry counter — it is stateless.

4. MORPHOLOGICAL \\w* suffix — "unsubscribed → still fails" trade-off.
   The regex r"\\b(subscribe)\\w*\\b" matches "subscribed", "subscribing",
   "subscriber", AND "unsubscribed" (because the word boundary fires at the
   word start and then "subscribe" matches inside "unsubscribed").
   This is intentional: zero false negatives on "subscribed" outweighs the
   occasional false positive on "unsubscribed" (a user-list concept, rarely
   encountered in DRHP Q&A prose).

5. CANONICAL ROOT via group.lastindex.
   The pattern has one capturing group per alternative. Python's re.Match.lastindex
   gives the index of the last participating group (which, for a single match, is
   the only participating group). match.group(match.lastindex) returns the canonical
   root form (e.g. "recommend" for "recommended", since \\w* is outside the group).

Wave 3 contract:
   - Import: `from compliance.scrubber import scrub, ScrubResult`
   - After LLM generate node, BEFORE cite-check node:
       result = scrub(grounded_answer.answer_prose)
       state["scrub_passed"] = result.passed
   - The graph conditional edge reads `state["scrub_passed"]` to decide whether
     to route to regenerate, refuse, or proceed to cite-check.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from compliance.banned_tokens import BANNED_TOKEN_PATTERN


@dataclass
class ScrubResult:
    """Result from the deterministic banned-token scrubber.

    Fields:
        passed:        True iff no banned token was found in the text.
        match:         The exact matched substring (e.g. "recommended") if
                       passed=False; None if passed=True.
        matched_token: The canonical root form of the matched token
                       (e.g. "recommend" not "recommended") if passed=False;
                       None if passed=True. Wave 3's generate-retry prompt
                       includes this to tell the LLM exactly which root to avoid.
    """

    passed: bool
    match: str | None
    matched_token: str | None


def scrub(text: str) -> ScrubResult:
    """Run the deterministic banned-token scrubber on a text string.

    Args:
        text: Any string — LLM output, UI copy, or test input.

    Returns:
        ScrubResult with passed=True and match/matched_token=None if no
        banned token found; ScrubResult with passed=False, match=<matched
        substring (full form including any suffix)>, matched_token=<canonical
        root form> if a banned token fires.

    Notes:
        - Only the FIRST match is returned (short-circuit). Wave 3 retries
          generation once; the retry prompt names the root token so the LLM
          can avoid all morphological variants in the regeneration.
        - Text is NFKC-normalized before matching to handle combining characters
          and Unicode space variants, but NOT to collapse homoglyphs (see
          module docstring §2).
        - The canonical root is extracted via match.lastindex, which gives the
          index of the participating capturing group. group(lastindex) is the
          root because \\w* is outside the group (see banned_tokens.py).
    """
    normalized = unicodedata.normalize("NFKC", text)
    m = BANNED_TOKEN_PATTERN.search(normalized)
    if m is None:
        return ScrubResult(passed=True, match=None, matched_token=None)

    # m.group(0) is the full matched string (e.g. "recommended" — includes \\w* suffix)
    full_match = m.group(0)

    # m.lastindex is the index of the last participating (non-None) capturing group.
    # Since only one branch fires per match, this is the only participating group.
    # group(lastindex) = canonical root (e.g. "recommend") because \\w* is outside.
    assert m.lastindex is not None, "Pattern must have capturing groups"
    canonical_root = m.group(m.lastindex).lower()

    return ScrubResult(passed=False, match=full_match, matched_token=canonical_root)
