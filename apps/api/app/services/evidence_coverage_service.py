from __future__ import annotations

import re

from app.schemas.evidence import EvidencePacket, EvidenceUnit
from app.schemas.reliability import (
    ClaimType,
    CoverageStatus,
    EvidenceCoverageReport,
    EvidenceRequirement,
)


class EvidenceCoverageService:
    _NUMBER_RE = re.compile(
        r"(?<![\w.])(?:\d+\s*/\s*\d+|\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?)(?!\w)"
    )
    _CLAIM_PATTERNS: dict[ClaimType, re.Pattern[str]] = {
        ClaimType.comparison: re.compile(
            r"\b(compare|compared|versus|vs|baseline|higher|lower|across|than|outperform)\b",
            re.IGNORECASE,
        ),
        ClaimType.taxonomy: re.compile(
            r"\b(classify|classification|taxonomy|category|label|archetype|risk type)\b",
            re.IGNORECASE,
        ),
        ClaimType.method: re.compile(
            r"\b(method|approach|architecture|algorithm|design|pipeline)\b",
            re.IGNORECASE,
        ),
        ClaimType.result: re.compile(
            r"\b(result|finding|evaluation|experiment|accuracy|success|rate|metric|report|reported)\b",
            re.IGNORECASE,
        ),
        ClaimType.recommendation: re.compile(
            r"\b(recommend|recommendation|mitigation|defense|policy|enforce|prevention|robust)\b",
            re.IGNORECASE,
        ),
        ClaimType.limitation: re.compile(
            r"\b(limitation|limitations|failure|threat|caveat|cannot|does not)\b",
            re.IGNORECASE,
        ),
        ClaimType.safety_boundary: re.compile(
            r"\b(overclaim|boundary|cannot support|should not claim|safe|safety guarantee)\b",
            re.IGNORECASE,
        ),
    }

    def evaluate(
        self,
        *,
        question: str,
        paper_ids: list[str] | None,
        requirement: EvidenceRequirement,
        packet: EvidencePacket | None,
    ) -> EvidenceCoverageReport:
        units = list(packet.units) if packet is not None else []
        selected_paper_ids = self._selected_paper_ids(paper_ids, units)
        covered_paper_ids = self._covered_paper_ids(selected_paper_ids, units)
        missing_paper_ids = (
            [paper_id for paper_id in selected_paper_ids if paper_id not in covered_paper_ids]
            if requirement.requires_multi_paper_coverage
            else []
        )

        evidence_text = " ".join(self._unit_text(unit) for unit in units)
        evidence_numbers = self._extract_numbers(evidence_text)
        question_numbers = self._extract_numbers(question)
        matched_numbers = [number for number in question_numbers if number in evidence_numbers]
        missing_numbers = [number for number in question_numbers if number not in evidence_numbers]

        covered_claim_types = self._covered_claim_types(evidence_text)
        missing_claim_types = [
            claim_type
            for claim_type in requirement.required_claim_types
            if claim_type not in covered_claim_types
        ]

        limits = self._limits(
            no_units=not units,
            missing_paper_ids=missing_paper_ids,
            missing_claim_types=missing_claim_types,
            missing_numbers=missing_numbers,
        )
        status = self._status(
            has_units=bool(units),
            covered_paper_ids=covered_paper_ids,
            missing_paper_ids=missing_paper_ids,
            covered_claim_types=covered_claim_types,
            missing_claim_types=missing_claim_types,
            matched_numbers=matched_numbers,
            missing_numbers=missing_numbers,
            requirement=requirement,
        )

        return EvidenceCoverageReport(
            requirement_id=requirement.requirement_id,
            status=status,
            covered_paper_ids=covered_paper_ids,
            missing_paper_ids=missing_paper_ids,
            covered_claim_types=covered_claim_types,
            missing_claim_types=missing_claim_types,
            matched_numbers=matched_numbers,
            missing_numbers=missing_numbers,
            targeted_queries=self._targeted_queries(
                missing_paper_ids=missing_paper_ids,
                missing_claim_types=missing_claim_types,
                missing_numbers=missing_numbers,
                requirement=requirement,
            ),
            limits=limits,
        )

    @staticmethod
    def _selected_paper_ids(paper_ids: list[str] | None, units: list[EvidenceUnit]) -> list[str]:
        if paper_ids:
            return list(paper_ids)
        selected: list[str] = []
        seen: set[str] = set()
        for unit in units:
            if unit.paper_id in seen:
                continue
            seen.add(unit.paper_id)
            selected.append(unit.paper_id)
        return selected

    @staticmethod
    def _covered_paper_ids(selected_paper_ids: list[str], units: list[EvidenceUnit]) -> list[str]:
        unit_paper_ids = {unit.paper_id for unit in units}
        return [paper_id for paper_id in selected_paper_ids if paper_id in unit_paper_ids]

    @staticmethod
    def _unit_text(unit: EvidenceUnit) -> str:
        parts = [unit.title or "", unit.caption or ""]
        if unit.metadata:
            parts.extend(str(value) for value in unit.metadata.values())
        return " ".join(part for part in parts if part)

    @classmethod
    def _extract_numbers(cls, text: str) -> list[str]:
        numbers: list[str] = []
        seen: set[str] = set()
        for match in cls._NUMBER_RE.finditer(text):
            number = re.sub(r"\s*/\s*", "/", match.group(0))
            if number in seen:
                continue
            seen.add(number)
            numbers.append(number)
        return numbers

    @classmethod
    def _covered_claim_types(cls, evidence_text: str) -> list[ClaimType]:
        covered: list[ClaimType] = []
        if cls._NUMBER_RE.search(evidence_text):
            covered.append(ClaimType.number)
        for claim_type in (
            ClaimType.comparison,
            ClaimType.taxonomy,
            ClaimType.method,
            ClaimType.result,
            ClaimType.recommendation,
            ClaimType.limitation,
            ClaimType.safety_boundary,
        ):
            if cls._CLAIM_PATTERNS[claim_type].search(evidence_text):
                covered.append(claim_type)
        return covered

    @staticmethod
    def _limits(
        *,
        no_units: bool,
        missing_paper_ids: list[str],
        missing_claim_types: list[ClaimType],
        missing_numbers: list[str],
    ) -> list[str]:
        limits: list[str] = []
        if no_units:
            return ["No accepted evidence is available."]
        if missing_paper_ids:
            limits.append("Missing required paper coverage.")
        if missing_claim_types:
            limits.append("Missing required claim-type coverage.")
        if missing_numbers:
            limits.append("Missing requested numeric evidence.")
        return limits

    @staticmethod
    def _status(
        *,
        has_units: bool,
        covered_paper_ids: list[str],
        missing_paper_ids: list[str],
        covered_claim_types: list[ClaimType],
        missing_claim_types: list[ClaimType],
        matched_numbers: list[str],
        missing_numbers: list[str],
        requirement: EvidenceRequirement,
    ) -> CoverageStatus:
        if not has_units:
            return CoverageStatus.insufficient

        required_dimension_count = 0
        covered_dimension_count = 0
        if requirement.requires_multi_paper_coverage:
            required_dimension_count += len(covered_paper_ids) + len(missing_paper_ids)
            covered_dimension_count += len(covered_paper_ids)
        if requirement.required_claim_types:
            required_dimension_count += len(requirement.required_claim_types)
            covered_dimension_count += len(
                [
                    claim_type
                    for claim_type in requirement.required_claim_types
                    if claim_type in covered_claim_types
                ]
            )
        if matched_numbers or missing_numbers:
            required_dimension_count += len(matched_numbers) + len(missing_numbers)
            covered_dimension_count += len(matched_numbers)

        if required_dimension_count > 0 and covered_dimension_count == 0:
            return CoverageStatus.insufficient
        if missing_paper_ids or missing_claim_types or missing_numbers:
            return CoverageStatus.partial
        return CoverageStatus.strong

    def _targeted_queries(
        self,
        *,
        missing_paper_ids: list[str],
        missing_claim_types: list[ClaimType],
        missing_numbers: list[str],
        requirement: EvidenceRequirement,
    ) -> list[str]:
        queries: list[str] = []
        claim_terms = self._claim_terms(list(requirement.required_claim_types))
        if missing_paper_ids:
            for paper_id in missing_paper_ids:
                queries.append(" ".join([paper_id, "reported", *claim_terms, "evidence"]))
        elif missing_claim_types:
            queries.append(" ".join([*self._claim_terms(missing_claim_types), "evidence"]))
        elif missing_numbers:
            queries.append("reported numbers evidence")

        return self._dedupe(queries)[: requirement.max_targeted_queries]

    @staticmethod
    def _claim_terms(claim_types: list[ClaimType]) -> list[str]:
        terms: list[str] = []
        for claim_type in claim_types:
            term = "numbers" if claim_type == ClaimType.number else claim_type.value
            if term not in terms:
                terms.append(term)
        return terms

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = " ".join(value.split())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped
