import json
from pathlib import Path

from app.services.evidence_requirement_service import EvidenceRequirementService


TESTSET_PATH = (
    Path(__file__).parents[3] / "eval" / "evidence_reliability_general_testset.json"
)


def test_general_reliability_eval_cases_map_to_expected_requirements() -> None:
    data = json.loads(TESTSET_PATH.read_text(encoding="utf-8"))

    assert data["name"] == "evidence_reliability_general_testset"
    assert "purpose" in data
    assert isinstance(data["cases"], list)
    assert 4 <= len(data["cases"]) <= 5

    service = EvidenceRequirementService()

    for case in data["cases"]:
        assert case["id"]
        assert case["question"]
        assert case["expected_intent"]
        assert isinstance(case.get("expected_claim_types", []), list)

        requirement = service.plan(question=case["question"], paper_ids=["p1", "p2"])

        assert requirement.intent.intent_type == case["expected_intent"]
        for claim_type in case.get("expected_claim_types", []):
            assert claim_type in requirement.required_claim_types
        if case.get("expected_multi_paper_coverage"):
            assert requirement.requires_multi_paper_coverage is True
