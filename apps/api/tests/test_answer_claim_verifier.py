from app.schemas.evidence import EvidencePacket, EvidenceUnit
from app.schemas.reliability import (
    EvidenceCoverageReport,
    EvidenceRequirement,
    QuestionIntent,
)
from app.services.answer_claim_verifier import AnswerClaimVerifier


def _requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="er-test",
        intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
        required_claim_types=["number", "recommendation"],
        must_verify_numeric_claims=True,
    )


def _coverage(status: str = "strong") -> EvidenceCoverageReport:
    return EvidenceCoverageReport(
        requirement_id="er-test",
        status=status,
        covered_paper_ids=["paper-1"],
        covered_claim_types=["number", "recommendation"],
        matched_numbers=["80%"],
    )


def _packet(caption: str) -> EvidencePacket:
    unit = EvidenceUnit(
        evidence_id="ev-paper-1-p2",
        paper_id="paper-1",
        page_number=2,
        source="hybrid_page",
        title="Runtime policy evaluation",
        caption=caption,
        metadata={"recommendation": "runtime policy enforcement"},
    )
    return EvidencePacket(
        packet_id="ep-test",
        query="Q?",
        paper_scope=["paper-1"],
        units=[unit],
        citations=[],
    )


def test_supported_claim_with_matching_number_and_text_is_strong() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The accepted evidence reports 80% success and recommends runtime policy enforcement.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The accepted evidence reports 80% success."),
    )

    assert report.status == "strong"
    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "supported"
    assert report.claims[0].evidence_ids == ["ev-paper-1-p2"]


def test_unseen_number_is_unsupported_and_partial() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The accepted evidence reports 94% success.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The accepted evidence reports 80% success."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
    assert "94%" in report.claims[0].reason


def test_broad_overclaim_is_unsupported_with_universal_reason() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The system detects all malware and guarantees safe execution.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evidence recommends runtime policy enforcement."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
    assert "Universal" in report.claims[0].reason
    assert "product-capability" in report.claims[0].reason


def test_bounded_all_claim_with_exact_evidence_is_supported() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The model reports results on all three datasets.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The model reports results on all three datasets."),
    )

    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "supported"
    assert "Universal" not in report.claims[0].reason


def test_universal_capability_claim_with_all_is_still_unsupported() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The system detects all malware and guarantees safe execution.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evidence recommends runtime policy enforcement."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
    assert "Universal" in report.claims[0].reason


def test_approach_guarantees_safe_execution_is_unsupported() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The approach guarantees safe execution.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evidence discusses runtime policy enforcement."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
    assert "Universal" in report.claims[0].reason


def test_method_guarantees_safe_execution_is_unsupported() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The method guarantees safe execution.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evidence discusses runtime policy enforcement."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
    assert "Universal" in report.claims[0].reason


def test_pronoun_guarantees_safe_execution_is_unsupported() -> None:
    report = AnswerClaimVerifier().verify(
        answer="It guarantees safe execution.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evidence discusses runtime policy enforcement."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
    assert "Universal" in report.claims[0].reason


def test_bounded_all_claim_still_not_unsupported_after_guarantee_tightening() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The model reports results on all three datasets.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The model reports results on all three datasets."),
    )

    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "supported"


def test_partially_supported_claim_downgrades_overall_status() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The evaluation discusses deployment readiness.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evidence recommends runtime policy enforcement."),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "partially_supported"


def test_supported_domain_topic_phrase_is_not_rejected_as_overclaim() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The evaluation measures malware detection on a benchmark.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The evaluation measures malware detection on a benchmark."),
    )

    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "supported"
    assert "Universal" not in report.claims[0].reason


def test_supported_safe_execution_phrase_is_not_rejected_as_overclaim() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The system evaluates safe execution conditions in a benchmark.",
        requirement=_requirement(),
        coverage=_coverage(),
        packet=_packet("The system evaluates safe execution conditions in a benchmark."),
    )

    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "supported"
    assert "Universal" not in report.claims[0].reason


def test_no_evidence_and_insufficient_coverage_is_insufficient() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The paper reports a result.",
        requirement=_requirement(),
        coverage=_coverage(status="insufficient"),
        packet=None,
    )

    assert report.status == "insufficient"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"
