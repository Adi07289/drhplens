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
    span_offsets: tuple[int, int] | None = Field(
        default=None,
        description="(start_char, end_char) within chunk_text that supports the claim; None if not extracted",
    )

    @field_validator("span_offsets")
    @classmethod
    def span_offsets_start_lte_end(
        cls, v: tuple[int, int] | None
    ) -> tuple[int, int] | None:
        """Reject inverted spans (start > end).

        STRIDE T-1-02: a corrupted span with start > end would produce a negative-length
        window in the cite-check algorithm, potentially leaking out-of-bounds content.
        Reject at schema validation time.
        """
        if v is None:
            return v
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
    span_offsets: tuple[int, int] = Field(
        ...,
        description="(start_char, end_char) in the source chunk text",
    )
    sources: list[RetrievedChunkRef] = Field(
        ...,
        min_length=1,
        description=">=1 retrieved chunk supporting this claim (PITFALL P18: never empty)",
    )

    @field_validator("span_offsets")
    @classmethod
    def span_offsets_start_lte_end(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Reject inverted spans (start > end). See STRIDE T-1-02."""
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
