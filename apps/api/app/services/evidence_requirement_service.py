import hashlib
import re

from app.schemas.reliability import EvidenceRequirement, QuestionIntent


class EvidenceRequirementService:
    _NUMERIC_PATTERN = re.compile(
        r"(\b(number|numbers|rate|rates|percent|percentage|scale|cost|token|tokens|how much)\b|\d)",
        re.IGNORECASE,
    )
    _TAXONOMY_PATTERN = re.compile(
        r"\b(classify|classification|taxonomy|label|category|archetype|risk type)\b",
        re.IGNORECASE,
    )
    _DEFENSE_PATTERN = re.compile(
        r"\b(defense|defence|mitigation|recommendation|secure|robust|safety|policy)\b",
        re.IGNORECASE,
    )
    _BOUNDARY_PATTERN = re.compile(
        r"\b(overclaim|limitation|limitations|should not claim|what should our report claim|cannot support|claim boundary)\b",
        re.IGNORECASE,
    )
    _METHOD_PATTERN = re.compile(
        r"\b(method|approach|experiment|result|finding|ablation|evaluation)\b",
        re.IGNORECASE,
    )
    _CROSS_DOC_PATTERN = re.compile(
        r"\b(across|compare|between|among|papers|documents|sources)\b",
        re.IGNORECASE,
    )

    def plan(self, *, question: str, paper_ids: list[str] | None) -> EvidenceRequirement:
        normalized_question = self._normalize_whitespace(question)
        ordered_paper_ids = list(paper_ids or [])
        intent_type = self._classify_intent(normalized_question)
        claim_types = self._derive_claim_types(intent_type)
        has_cross_doc_terms = bool(self._CROSS_DOC_PATTERN.search(normalized_question))
        requires_multi_paper_coverage = (
            len(ordered_paper_ids) > 1
            and (
                has_cross_doc_terms
                or intent_type
                in {
                    "numeric_grounding",
                    "cross_document_comparison",
                    "taxonomy_classification",
                }
            )
        )

        return EvidenceRequirement(
            requirement_id=self._stable_requirement_id(normalized_question, ordered_paper_ids),
            intent=QuestionIntent(intent_type=intent_type, confidence=0.9),
            required_claim_types=claim_types,
            requires_multi_paper_coverage=requires_multi_paper_coverage,
            minimum_relevant_pages_per_paper=1 if requires_multi_paper_coverage else 0,
            must_verify_numeric_claims=intent_type == "numeric_grounding",
            allow_inference="labeled_only",
            max_targeted_queries=4,
        )

    def _classify_intent(self, question: str) -> str:
        if self._BOUNDARY_PATTERN.search(question):
            return "claim_boundary"
        if self._NUMERIC_PATTERN.search(question):
            return "numeric_grounding"
        if self._TAXONOMY_PATTERN.search(question):
            return "taxonomy_classification"
        if self._DEFENSE_PATTERN.search(question):
            return "defense_or_recommendation"
        if self._CROSS_DOC_PATTERN.search(question):
            return "cross_document_comparison"
        if self._METHOD_PATTERN.search(question):
            return "method_or_result_extraction"
        return "general_paper_qa"

    @staticmethod
    def _derive_claim_types(intent_type: str) -> list[str]:
        claim_types: list[str] = []

        def add(*values: str) -> None:
            for value in values:
                if value not in claim_types:
                    claim_types.append(value)

        if intent_type == "numeric_grounding":
            add("number", "comparison", "method", "result")
        elif intent_type == "taxonomy_classification":
            add("taxonomy")
        elif intent_type == "method_or_result_extraction":
            add("method", "result")
        elif intent_type == "defense_or_recommendation":
            add("recommendation")
        elif intent_type == "claim_boundary":
            add("recommendation", "safety_boundary", "limitation")
        elif intent_type == "cross_document_comparison":
            add("comparison", "result")
        else:
            add("result")

        return claim_types

    @staticmethod
    def _normalize_whitespace(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _stable_requirement_id(question: str, paper_ids: list[str]) -> str:
        seed = "\n".join([question.lower(), *paper_ids])
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
        return f"er-{digest}"
