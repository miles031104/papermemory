from app.schemas.reliability import (
    AnswerQualityStatus,
    AnswerReliabilityReport,
    ClaimSupport,
    EvidenceCoverageReport,
    EvidenceRequirement,
    QuestionIntent,
)
from app.services.evidence_requirement_service import EvidenceRequirementService


def test_evidence_requirement_serializes_to_json_payload() -> None:
    requirement = EvidenceRequirement(
        intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
        required_claim_types=["number", "comparison"],
        requires_multi_paper_coverage=True,
        minimum_relevant_pages_per_paper=1,
        must_verify_numeric_claims=True,
        allow_inference="labeled_only",
    )

    assert requirement.model_dump(mode="json") == {
        "requirement_id": "er-default",
        "intent": {
            "intent_type": "numeric_grounding",
            "confidence": 0.9,
            "rationale": None,
        },
        "required_claim_types": ["number", "comparison"],
        "requires_multi_paper_coverage": True,
        "minimum_relevant_pages_per_paper": 1,
        "must_verify_numeric_claims": True,
        "allow_inference": "labeled_only",
        "max_targeted_queries": 4,
    }


def test_evidence_coverage_report_preserves_fields() -> None:
    report = EvidenceCoverageReport(
        requirement_id="er-test",
        status="partial",
        covered_paper_ids=["paper-a"],
        missing_paper_ids=["paper-b"],
        covered_claim_types=["number"],
        missing_claim_types=["comparison"],
        targeted_queries=["paper-b comparison numeric evidence"],
        limits=["Missing required paper coverage."],
    )

    assert report.model_dump(mode="json") == {
        "requirement_id": "er-test",
        "status": "partial",
        "covered_paper_ids": ["paper-a"],
        "missing_paper_ids": ["paper-b"],
        "covered_claim_types": ["number"],
        "missing_claim_types": ["comparison"],
        "matched_numbers": [],
        "missing_numbers": [],
        "targeted_queries": ["paper-b comparison numeric evidence"],
        "limits": ["Missing required paper coverage."],
    }


def test_claim_support_preserves_unsupported_broad_claim() -> None:
    support = ClaimSupport(
        claim_text="This broad claim is not supported by the selected evidence.",
        support_status="unsupported",
        evidence_ids=[],
        reason="The evidence packet does not contain direct support.",
    )

    assert support.model_dump(mode="json") == {
        "claim_text": "This broad claim is not supported by the selected evidence.",
        "support_status": "unsupported",
        "evidence_ids": [],
        "reason": "The evidence packet does not contain direct support.",
    }
    assert AnswerQualityStatus("partial") == "partial"


def test_answer_reliability_report_defaults_unsupported_claim_count() -> None:
    requirement = EvidenceRequirement(
        intent=QuestionIntent(intent_type="general_paper_qa"),
        required_claim_types=["result"],
    )
    coverage = EvidenceCoverageReport(
        requirement_id=requirement.requirement_id,
        status="strong",
        covered_claim_types=["result"],
    )

    report = AnswerReliabilityReport(
        status="strong",
        requirement=requirement,
        coverage=coverage,
    )

    assert report.unsupported_claim_count == 0
    assert report.model_dump(mode="json")["unsupported_claim_count"] == 0


def test_plan_numeric_cross_document_question_requires_numbers_and_comparisons() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Which concrete numbers across these papers show the threat is real?",
        paper_ids=["p1", "p2", "p3"],
    )

    assert requirement.intent.intent_type == "numeric_grounding"
    assert requirement.requires_multi_paper_coverage is True
    assert requirement.minimum_relevant_pages_per_paper == 1
    assert requirement.must_verify_numeric_claims is True
    assert "number" in requirement.required_claim_types
    assert "comparison" in requirement.required_claim_types


def test_plan_generic_cross_document_comparison_is_not_numeric_grounding() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Compare the main findings across the selected papers.",
        paper_ids=["p1", "p2"],
    )

    assert requirement.intent.intent_type == "cross_document_comparison"
    assert requirement.requires_multi_paper_coverage is True
    assert "comparison" in requirement.required_claim_types
    assert "result" in requirement.required_claim_types
    assert requirement.must_verify_numeric_claims is False


def test_plan_generic_cross_document_result_comparison_wins_over_method_extraction() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Compare the main result across the selected papers.",
        paper_ids=["p1", "p2"],
    )

    assert requirement.intent.intent_type == "cross_document_comparison"
    assert requirement.requires_multi_paper_coverage is True
    assert "comparison" in requirement.required_claim_types
    assert "result" in requirement.required_claim_types
    assert requirement.must_verify_numeric_claims is False


def test_plan_generic_cross_document_finding_comparison_wins_over_method_extraction() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Compare the main finding across the selected papers.",
        paper_ids=["p1", "p2"],
    )

    assert requirement.intent.intent_type == "cross_document_comparison"
    assert requirement.requires_multi_paper_coverage is True
    assert "comparison" in requirement.required_claim_types
    assert "result" in requirement.required_claim_types
    assert requirement.must_verify_numeric_claims is False


def test_plan_taxonomy_question_requires_labeled_multi_paper_taxonomy() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Classify this risk using the papers and explain which source supports each label.",
        paper_ids=["p1", "p2"],
    )

    assert requirement.intent.intent_type == "taxonomy_classification"
    assert requirement.requires_multi_paper_coverage is True
    assert "taxonomy" in requirement.required_claim_types
    assert requirement.allow_inference == "labeled_only"


def test_plan_claim_boundary_question_requires_safety_boundary() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="What should our report claim and what should it not overclaim?",
        paper_ids=["p1"],
    )

    assert requirement.intent.intent_type == "claim_boundary"
    assert "safety_boundary" in requirement.required_claim_types
    assert requirement.allow_inference == "labeled_only"


def test_plan_paper_report_result_question_is_not_claim_boundary() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="What result does the paper report?",
        paper_ids=["p1"],
    )

    assert requirement.intent.intent_type == "method_or_result_extraction"
    assert "result" in requirement.required_claim_types
    assert "safety_boundary" not in requirement.required_claim_types


def test_plan_ids_are_stable_and_generic() -> None:
    service = EvidenceRequirementService()
    question = "Which concrete numbers across these papers show the threat is real?"

    first = service.plan(question=question, paper_ids=["p1", "p2", "p3"])
    second = service.plan(
        question="  Which concrete numbers across these papers show the threat is real?  ",
        paper_ids=["p1", "p2", "p3"],
    )

    assert first.requirement_id == second.requirement_id
    assert first.requirement_id.startswith("er-")
    assert "p1" not in first.requirement_id
    assert "paper" not in first.requirement_id
