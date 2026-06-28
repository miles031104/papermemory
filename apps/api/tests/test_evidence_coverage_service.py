from app.schemas.evidence import EvidenceCitation, EvidencePacket, EvidenceUnit
from app.schemas.reliability import (
    ClaimType,
    EvidenceRequirement,
    QuestionIntent,
    QuestionIntentType,
)
from app.services.evidence_coverage_service import EvidenceCoverageService


def _requirement(
    *,
    claim_types: list[ClaimType],
    intent_type: QuestionIntentType = QuestionIntentType.numeric_grounding,
    multi: bool = False,
    must_verify_numeric: bool = False,
) -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="er-test",
        intent=QuestionIntent(intent_type=intent_type, confidence=0.9),
        required_claim_types=claim_types,
        requires_multi_paper_coverage=multi,
        minimum_relevant_pages_per_paper=1 if multi else 0,
        must_verify_numeric_claims=must_verify_numeric,
        max_targeted_queries=4,
    )


def _unit(paper_id: str, caption: str, *, title: str | None = None) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=f"ev-{paper_id}-1",
        paper_id=paper_id,
        page_number=1,
        source="hybrid_page",
        score=0.9,
        title=title,
        caption=caption,
        validation_state="validated",
    )


def _packet(units: list[EvidenceUnit]) -> EvidencePacket:
    return EvidencePacket(
        packet_id="ep-test",
        query="test",
        paper_scope=[unit.paper_id for unit in units],
        units=units,
        citations=[
            EvidenceCitation(
                evidence_id=unit.evidence_id,
                paper_id=unit.paper_id,
                page_number=unit.page_number,
            )
            for unit in units
        ],
        limits=[],
    )


def test_missing_paper_for_multi_paper_numeric_question_targets_missing_paper() -> None:
    requirement = _requirement(
        claim_types=[ClaimType.number, ClaimType.comparison],
        multi=True,
        must_verify_numeric=True,
    )
    report = EvidenceCoverageService().evaluate(
        question="Compare the reported accuracy numbers across papers.",
        paper_ids=["p1", "p2"],
        requirement=requirement,
        packet=_packet([_unit("p1", "Accuracy is 80%.")]),
    )

    assert report.status == "partial"
    assert report.covered_paper_ids == ["p1"]
    assert report.missing_paper_ids == ["p2"]
    assert report.targeted_queries == ["p2 reported numbers comparison evidence"]


def test_matches_numbers_from_question_and_evidence() -> None:
    requirement = _requirement(claim_types=[ClaimType.number], must_verify_numeric=True)
    report = EvidenceCoverageService().evaluate(
        question="Does the evidence support 80% and 94%?",
        paper_ids=["p1", "p2"],
        requirement=requirement,
        packet=_packet([_unit("p1", "80%"), _unit("p2", "94%")]),
    )

    assert report.status == "strong"
    assert report.matched_numbers == ["80%", "94%"]
    assert report.missing_numbers == []
    assert report.targeted_queries == []


def test_missing_numeric_claim_type_adds_numbers_targeted_query() -> None:
    requirement = _requirement(claim_types=[ClaimType.number], must_verify_numeric=True)
    report = EvidenceCoverageService().evaluate(
        question="What number supports the result?",
        paper_ids=["p1"],
        requirement=requirement,
        packet=_packet([_unit("p1", "The method is discussed without quantitative results.")]),
    )

    assert report.status in {"partial", "insufficient"}
    assert ClaimType.number in report.missing_claim_types
    assert any("numbers" in query for query in report.targeted_queries)


def test_no_evidence_is_insufficient_with_no_accepted_evidence_limit() -> None:
    requirement = _requirement(claim_types=[ClaimType.result])
    report = EvidenceCoverageService().evaluate(
        question="What result is reported?",
        paper_ids=["p1"],
        requirement=requirement,
        packet=None,
    )

    assert report.status == "insufficient"
    assert report.limits == ["No accepted evidence is available."]


def test_taxonomy_requirement_is_strong_when_taxonomy_evidence_appears() -> None:
    requirement = _requirement(
        claim_types=[ClaimType.taxonomy],
        intent_type=QuestionIntentType.taxonomy_classification,
    )
    report = EvidenceCoverageService().evaluate(
        question="Which taxonomy category label is supported?",
        paper_ids=["p1"],
        requirement=requirement,
        packet=_packet([_unit("p1", "The taxonomy category label is described.")]),
    )

    assert report.status == "strong"
    assert report.covered_claim_types == [ClaimType.taxonomy]
    assert report.targeted_queries == []
