"""
Pydantic v2 schemas — the load-bearing cross-phase contract for DRHPLens.

These five classes are locked in SKELETON §B. Phase 3 METHOD-01 consumes them
verbatim. Renaming or removing fields without a phase-protocol break discussion
is forbidden. The claim_id regex pattern r'^c_[a-z0-9]{6,16}$' is a canonical
invariant; changing it breaks Phase 3's claim-ID renderer.

STRIDE T-1-02 mitigation: span_offsets validator rejects start > end, preventing
a corrupted span from reaching the cite-check window code with an inverted window.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class RetrievedChunkRef(BaseModel):
    """Reference to one retrieved DRHP chunk used as evidence for a claim.

    Field names align with ChunkPayload in storage/vector.py (Wave 2) — do NOT
    rename without updating that module and all downstream usages simultaneously.
    """

    chunk_id: str = Field(..., description="UUID of the chunk in Qdrant payload")
    page_start: int = Field(..., description="First DRHP page number covered by this chunk")
    page_end: int = Field(..., description="Last DRHP page number covered by this chunk")
    printed_page_label: str | None = Field(
        default=None,
        description="Human-readable page label (e.g. 'iv', '12'); None if unknown",
    )
    section: str = Field(..., description="DRHP section name, e.g. 'Risk Factors'")
    score: float | None = Field(
        default=None,
        description="Retrieval/reranking score for this chunk; None if not computed",
    )
    verbatim_span: str | None = Field(
        default=None,
        description="Verbatim text snippet from the chunk that supports the claim; None if not extracted",
    )
    span_offsets: list[int] | None = Field(
        default=None,
        description="[start_char, end_char] within chunk_text that supports the claim; None if not extracted",
    )

    @field_validator("span_offsets")
    @classmethod
    def span_offsets_start_lte_end(
        cls, v: list[int] | None
    ) -> list[int] | None:
        """Reject malformed spans (wrong length or start > end).

        STRIDE T-1-02: a corrupted span with start > end would produce a negative-length
        window in the cite-check algorithm, potentially leaking out-of-bounds content.
        Reject at schema validation time. (list[int], not tuple, because Google GenAI's
        structured-output schema rejects fixed-length tuples / prefixItems.)
        """
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError(f"span_offsets must have exactly 2 elements, got {len(v)}")
        start, end = v
        if start > end:
            raise ValueError(
                f"span_offsets start ({start}) must be <= end ({end})"
            )
        return v


class Claim(BaseModel):
    """A single factual claim emitted by the LLM.

    The claim_id regex pattern r'^c_[a-z0-9]{6,16}$' is the canonical cross-phase
    contract per SKELETON §B. Changing it breaks Phase 3's claim-ID renderer
    (METHOD-01 consumes this schema verbatim).

    PITFALL P18 antibody: sources is min_length=1, so the LLM can never emit a
    claim without at least one retrieved-chunk source.
    """

    claim_id: str = Field(
        ...,
        pattern=r"^c_[a-z0-9]{6,16}$",
        description="Stable per-answer id, e.g. c_4f3a8b. Regex enforces lowercase hex.",
    )
    text: str = Field(
        ...,
        description="The verbatim claim text as it appears in the answer prose",
    )
    source_chunk_id: str = Field(
        ...,
        description="Primary chunk_id reference (convenience field; full source list in sources)",
    )
    drhp_page: int = Field(
        ...,
        description="Primary DRHP page number for UI citation display",
    )
    section: str = Field(
        ...,
        description="DRHP section name for the primary source chunk",
    )
    verbatim_span: str = Field(
        ...,
        description="Verbatim text from the source that supports this claim",
    )
    span_offsets: list[int] = Field(
        ...,
        description="[start_char, end_char] in the source chunk text",
    )
    sources: list[RetrievedChunkRef] = Field(
        ...,
        min_length=1,
        description=">=1 retrieved chunk supporting this claim (PITFALL P18: never empty)",
    )

    @field_validator("span_offsets")
    @classmethod
    def span_offsets_start_lte_end(cls, v: list[int]) -> list[int]:
        """Reject malformed spans (wrong length or start > end). See STRIDE T-1-02.

        list[int], not tuple, because Google GenAI structured output rejects tuples.
        """
        if len(v) != 2:
            raise ValueError(f"span_offsets must have exactly 2 elements, got {len(v)}")
        start, end = v
        if start > end:
            raise ValueError(
                f"span_offsets start ({start}) must be <= end ({end})"
            )
        return v


# Locked vocabulary — Wave 3 nodes branch on these exact string values.
# Do NOT add or rename values without updating every branch in agent/graph.py.
RefusalReason = Literal[
    "low_retrieval_score",
    "unsupported_claim",
    "banned_token",
    "infrastructure_error",
]


class GroundedAnswer(BaseModel):
    """The structured answer the LLM must emit, validated by Instructor.

    answer_prose contains {{claim_id}} placeholders. The Wave 4 renderer resolves
    each placeholder to a numbered superscript chip via the dedup logic in
    ui/citation_chip.py. D-06: sub_question_addressed and sub_question_unaddressed
    default to [] so single-question answers don't require explicit empty lists.
    """

    answer_prose: str = Field(
        ...,
        description=(
            "Full prose answer with inline {{claim_id}} markers. "
            "Renderer replaces each with a numbered superscript chip."
        ),
    )
    claims: list[Claim] = Field(
        ...,
        description="All claims referenced in answer_prose",
    )
    sub_question_addressed: list[str] = Field(
        default_factory=list,
        description="If multi-part Q (D-06), the sub-questions this answer covers",
    )
    sub_question_unaddressed: list[str] = Field(
        default_factory=list,
        description="Sub-questions the DRHP does not address (rendered as flag, D-06)",
    )

    @model_validator(mode="after")
    def claim_ids_unique_within_answer(self) -> "GroundedAnswer":
        """Ensure every claim_id is unique within a single answer.

        Duplicate claim_ids would cause the chip renderer to produce ambiguous chips.
        """
        ids = [c.claim_id for c in self.claims]
        if len(ids) != len(set(ids)):
            dupes = [cid for cid in ids if ids.count(cid) > 1]
            raise ValueError(
                f"claim_id values must be unique within a GroundedAnswer; duplicates: {set(dupes)}"
            )
        return self


class RefusalResponse(BaseModel):
    """Structured refusal returned when dual-gate rejects a question.

    reformulation_suggestions is max_length=3 per UI-SPEC §Visuals — Refusal Banner
    Contract: "up to three clickable chips".
    """

    reason: RefusalReason = Field(
        ...,
        description="Locked vocabulary; Wave 3 branches on this value",
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of why the question was refused",
    )
    reformulation_suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Up to 3 clickable chip suggestions for the user to try next",
    )


class ToolClaim(BaseModel):
    """A tool-derived claim/number with NON-DRHP provenance (Phase 6.3 D-03, RESEARCH caveat e).

    A SIBLING of Claim — deliberately NOT a Claim subclass. Peer / forecast / red-flag
    numbers have no DRHP chunk, page, or verbatim span, so they carry provenance to
    their committed-artifact source record instead. ToolClaim omits every DRHP-span
    field (drhp_page / verbatim_span / span_offsets / sources); inventing those for a
    tool number would fabricate a DRHP grounding it does not have (honesty invariant),
    which is exactly why subclassing Claim was rejected in favour of a discriminated union.

    claim_id reuses the EXACT locked cross-phase pattern r'^c_[a-z0-9]{6,16}$' (SKELETON
    §B) so the Phase-3 claim-ID chip renderer resolves a ToolClaim chip the same way it
    resolves a Claim chip — the FusedAnswer union is render-uniform on claim_id (UI-SPEC C2).
    """

    claim_id: str = Field(
        ...,
        pattern=r"^c_[a-z0-9]{6,16}$",
        description="Stable per-answer id; SAME regex as Claim so the chip renderer resolves it.",
    )
    text: str = Field(
        ...,
        description="The verbatim claim text as it appears in the fused answer prose",
    )
    value: float | str = Field(
        ...,
        description="The tool-derived value: a number, or a string like 'not disclosed' (numeric-faithfulness).",
    )
    source_tool: Literal["query_peers", "query_forecast", "query_redflags"] = Field(
        ...,
        description="Which read-only tool produced this number (GMP folds into query_forecast, D-04)",
    )
    source_record_id: str = Field(
        ...,
        description="The committed record the number traces to: a data/*.json path + field (D-03 provenance)",
    )


class FusedAnswer(BaseModel):
    """The fused multi-tool answer — one cited answer weaving DRHP text + tool numbers (D-03).

    answer_prose carries {{claim_id}} markers resolved by the same chip renderer as
    GroundedAnswer. claims is a discriminated union: DRHP-grounded Claims run the
    existing span cite-check unchanged; ToolClaims reconcile their number against the
    source record (extended cite-check dispatches on type — RESEARCH caveat e). is_partial
    + unaddressed carry the D-08 honest-partial posture (return whatever grounded content
    exists, explicitly labelled incomplete — never fabricate the missing part).
    """

    answer_prose: str = Field(
        ...,
        description=(
            "Full fused prose with inline {{claim_id}} markers. "
            "Renderer replaces each with a numbered (Claim) or lettered (ToolClaim) chip."
        ),
    )
    claims: list[Claim | ToolClaim] = Field(
        ...,
        description="Discriminated union of DRHP-grounded Claims and tool-derived ToolClaims",
    )
    is_partial: bool = Field(
        default=False,
        description="D-08: True iff this is an honest labelled partial (tool abstain/error or budget-trip)",
    )
    unaddressed: list[str] = Field(
        default_factory=list,
        description="Parts the answer could not cover (rendered as an honest 'ran out of steps' flag, D-08)",
    )

    @model_validator(mode="after")
    def claim_ids_unique_within_answer(self) -> "FusedAnswer":
        """Ensure every claim_id is unique across the whole Claim | ToolClaim union.

        Ported from GroundedAnswer: duplicate claim_ids — whether two Claims, two
        ToolClaims, or one of each — would make the chip renderer produce ambiguous chips.
        """
        ids = [c.claim_id for c in self.claims]
        if len(ids) != len(set(ids)):
            dupes = [cid for cid in ids if ids.count(cid) > 1]
            raise ValueError(
                f"claim_id values must be unique within a FusedAnswer; duplicates: {set(dupes)}"
            )
        return self
