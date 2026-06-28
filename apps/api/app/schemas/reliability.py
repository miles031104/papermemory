from enum import StrEnum

from pydantic import BaseModel, Field


class QuestionIntentType(StrEnum):
    numeric_grounding = "numeric_grounding"
    cross_document_comparison = "cross_document_comparison"
    taxonomy_classification = "taxonomy_classification"
    method_or_result_extraction = "method_or_result_extraction"
    defense_or_recommendation = "defense_or_recommendation"
    claim_boundary = "claim_boundary"
    general_paper_qa = "general_paper_qa"


class ClaimType(StrEnum):
    number = "number"
    comparison = "comparison"
    taxonomy = "taxonomy"
    method = "method"
    result = "result"
    recommendation = "recommendation"
    limitation = "limitation"
    safety_boundary = "safety_boundary"


class InferencePolicy(StrEnum):
    none = "none"
    labeled_only = "labeled_only"
    allowed = "allowed"


class CoverageStatus(StrEnum):
    strong = "strong"
    partial = "partial"
    insufficient = "insufficient"


class AnswerQualityStatus(StrEnum):
    strong = "strong"
    partial = "partial"
    insufficient = "insufficient"


class ClaimSupportStatus(StrEnum):
    supported = "supported"
    partially_supported = "partially_supported"
    unsupported = "unsupported"


class QuestionIntent(BaseModel):
    intent_type: QuestionIntentType
    confidence: float = Field(default=0.5, ge=0, le=1)
    rationale: str | None = Field(default=None, max_length=240)


class EvidenceRequirement(BaseModel):
    requirement_id: str = "er-default"
    intent: QuestionIntent
    required_claim_types: list[ClaimType] = Field(default_factory=list)
    requires_multi_paper_coverage: bool = False
    minimum_relevant_pages_per_paper: int = Field(default=0, ge=0, le=5)
    must_verify_numeric_claims: bool = False
    allow_inference: InferencePolicy = InferencePolicy.labeled_only
    max_targeted_queries: int = Field(default=4, ge=0, le=8)


class EvidenceCoverageReport(BaseModel):
    requirement_id: str
    status: CoverageStatus
    covered_paper_ids: list[str] = Field(default_factory=list)
    missing_paper_ids: list[str] = Field(default_factory=list)
    covered_claim_types: list[ClaimType] = Field(default_factory=list)
    missing_claim_types: list[ClaimType] = Field(default_factory=list)
    matched_numbers: list[str] = Field(default_factory=list)
    missing_numbers: list[str] = Field(default_factory=list)
    targeted_queries: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)


class ClaimSupport(BaseModel):
    claim_text: str = Field(max_length=800)
    support_status: ClaimSupportStatus
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str = Field(max_length=400)


class AnswerReliabilityReport(BaseModel):
    status: AnswerQualityStatus
    requirement: EvidenceRequirement
    coverage: EvidenceCoverageReport
    claims: list[ClaimSupport] = Field(default_factory=list)
    unsupported_claim_count: int = Field(default=0, ge=0)
    limits: list[str] = Field(default_factory=list)
