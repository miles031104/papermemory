from __future__ import annotations

import re

from app.schemas.evidence import EvidencePacket, EvidenceUnit
from app.schemas.reliability import (
    AnswerQualityStatus,
    AnswerReliabilityReport,
    ClaimSupport,
    ClaimSupportStatus,
    CoverageStatus,
    EvidenceCoverageReport,
    EvidenceRequirement,
)

UNSUPPORTED_CLAIM_LIMIT = "One or more answer claims are not supported by accepted evidence."


class AnswerClaimVerifier:
    _NUMBER_RE = re.compile(
        r"(?<![\w.])(?:\d+\s*/\s*\d+|\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?)(?!\w)"
    )
    _TOKEN_RE = re.compile(r"[a-z][a-z0-9_-]{2,}", re.IGNORECASE)
    _BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
    _SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
    _UNIVERSAL_OVERCLAIM_RE = re.compile(
        r"\b("
        r"always|guarantee|guarantees|guaranteed|detects\s+all|prevents\s+all"
        r")\b",
        re.IGNORECASE,
    )
    _OPEN_ENDED_ALL_CAPABILITY_RE = re.compile(
        r"\b(?:handles?|supports?|covers?|protects?|secures?|prevents?|detects?|blocks?|stops?)\s+all\b",
        re.IGNORECASE,
    )
    _GUARANTEE_CAPABILITY_RE = re.compile(
        r"\bguarantee(?:s|d)?\b.*\b("
        r"safe(?:ty)?|secure|security|execution|correct(?:ness)?|complete|"
        r"prevent|prevents|detect|detects|protect|protects|block|blocks|"
        r"success|accuracy|coverage|reliable|reliability"
        r")\b",
        re.IGNORECASE,
    )
    _BOUNDED_ALL_SCOPE_RE = re.compile(
        r"\ball\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:datasets?|classes?|pages?|papers?|documents?|benchmarks?|cases?|conditions?|"
        r"tasks?|metrics?|experiments?|baselines?|categories?)\b",
        re.IGNORECASE,
    )
    _PRODUCT_CAPABILITY_RE = re.compile(
        r"\b(system|product|tool|platform|model|agent|runtime|pipeline|defense|defence)\b",
        re.IGNORECASE,
    )
    _STOPWORDS = {
        "the",
        "and",
        "for",
        "from",
        "that",
        "this",
        "with",
        "into",
        "does",
        "not",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "its",
        "their",
        "paper",
        "evidence",
        "accepted",
    }

    def verify(
        self,
        *,
        answer: str,
        requirement: EvidenceRequirement,
        coverage: EvidenceCoverageReport,
        packet: EvidencePacket | None,
    ) -> AnswerReliabilityReport:
        evidence_text_by_id = self._evidence_text_by_id(packet)
        evidence_text = " ".join(evidence_text_by_id.values())
        evidence_numbers = set(self._extract_numbers(evidence_text))
        evidence_tokens = self._content_tokens(evidence_text)

        claims: list[ClaimSupport] = []
        for claim_text in self._claim_like_fragments(answer):
            claim = self._verify_claim(
                claim_text=claim_text,
                evidence_text_by_id=evidence_text_by_id,
                evidence_text=evidence_text,
                evidence_numbers=evidence_numbers,
                evidence_tokens=evidence_tokens,
            )
            claims.append(claim)

        unsupported_count = sum(
            1 for claim in claims if claim.support_status == ClaimSupportStatus.unsupported
        )
        partially_supported_count = sum(
            1 for claim in claims if claim.support_status == ClaimSupportStatus.partially_supported
        )
        limits = list(coverage.limits)
        if unsupported_count > 0 and UNSUPPORTED_CLAIM_LIMIT not in limits:
            limits.append(UNSUPPORTED_CLAIM_LIMIT)

        return AnswerReliabilityReport(
            status=self._status(
                coverage=coverage,
                unsupported_count=unsupported_count,
                partially_supported_count=partially_supported_count,
            ),
            requirement=requirement,
            coverage=coverage,
            claims=claims,
            unsupported_claim_count=unsupported_count,
            limits=limits,
        )

    def _verify_claim(
        self,
        *,
        claim_text: str,
        evidence_text_by_id: dict[str, str],
        evidence_text: str,
        evidence_numbers: set[str],
        evidence_tokens: set[str],
    ) -> ClaimSupport:
        if self._is_broad_overclaim(claim_text):
            return ClaimSupport(
                claim_text=claim_text,
                support_status=ClaimSupportStatus.unsupported,
                evidence_ids=[],
                reason="Universal product-capability claim is not supported by accepted evidence.",
            )

        claim_numbers = self._extract_numbers(claim_text)
        missing_numbers = [number for number in claim_numbers if number not in evidence_numbers]
        if missing_numbers:
            return ClaimSupport(
                claim_text=claim_text,
                support_status=ClaimSupportStatus.unsupported,
                evidence_ids=[],
                reason=f"Numeric claim includes missing numbers: {', '.join(missing_numbers)}.",
            )

        if not evidence_text.strip():
            return ClaimSupport(
                claim_text=claim_text,
                support_status=ClaimSupportStatus.unsupported,
                evidence_ids=[],
                reason="No accepted evidence text is available for this claim.",
            )

        claim_tokens = self._content_tokens(claim_text)
        overlap = claim_tokens & evidence_tokens
        if self._has_enough_overlap(claim_tokens, overlap):
            return ClaimSupport(
                claim_text=claim_text,
                support_status=ClaimSupportStatus.supported,
                evidence_ids=self._matching_evidence_ids(claim_tokens, evidence_text_by_id),
                reason="Claim tokens overlap accepted evidence text.",
            )

        return ClaimSupport(
            claim_text=claim_text,
            support_status=ClaimSupportStatus.partially_supported,
            evidence_ids=[],
            reason="Accepted evidence exists, but direct claim support is weak.",
        )

    @classmethod
    def _claim_like_fragments(cls, answer: str) -> list[str]:
        normalized = cls._BULLET_RE.sub("", answer)
        fragments: list[str] = []
        seen: set[str] = set()
        for raw_fragment in cls._SENTENCE_SPLIT_RE.split(normalized):
            fragment = raw_fragment.strip(" \t\r\n-*")
            if not fragment:
                continue
            if len(fragment) < 18 and len(cls._content_tokens(fragment)) < 3:
                continue
            dedupe_key = fragment.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            fragments.append(fragment[:800])
            if len(fragments) >= 12:
                break
        return fragments

    @classmethod
    def _evidence_text_by_id(cls, packet: EvidencePacket | None) -> dict[str, str]:
        if packet is None:
            return {}
        return {
            unit.evidence_id: cls._unit_text(unit)
            for unit in packet.units
            if cls._unit_text(unit).strip()
        }

    @staticmethod
    def _unit_text(unit: EvidenceUnit) -> str:
        parts = [unit.title or "", unit.caption or ""]
        if unit.metadata:
            parts.extend(str(value) for value in unit.metadata.values())
        return " ".join(part for part in parts if part)

    @classmethod
    def _extract_numbers(cls, text: str) -> list[str]:
        return [re.sub(r"\s*/\s*", "/", match.group(0)) for match in cls._NUMBER_RE.finditer(text)]

    @classmethod
    def _content_tokens(cls, text: str) -> set[str]:
        return {
            token.lower()
            for token in cls._TOKEN_RE.findall(text)
            if token.lower() not in cls._STOPWORDS
        }

    @classmethod
    def _is_broad_overclaim(cls, claim_text: str) -> bool:
        if cls._GUARANTEE_CAPABILITY_RE.search(claim_text):
            return True

        has_universal_trigger = bool(cls._UNIVERSAL_OVERCLAIM_RE.search(claim_text))
        if (
            not has_universal_trigger
            and cls._OPEN_ENDED_ALL_CAPABILITY_RE.search(claim_text)
            and not cls._BOUNDED_ALL_SCOPE_RE.search(claim_text)
        ):
            has_universal_trigger = True

        return has_universal_trigger and (
            bool(cls._PRODUCT_CAPABILITY_RE.search(claim_text))
            or bool(re.search(r"\b(detects\s+all|prevents\s+all)\b", claim_text, re.IGNORECASE))
        )

    @staticmethod
    def _has_enough_overlap(claim_tokens: set[str], overlap: set[str]) -> bool:
        if not claim_tokens:
            return False
        return len(overlap) >= min(3, len(claim_tokens)) or (
            len(overlap) >= 2 and len(overlap) / len(claim_tokens) >= 0.4
        )

    @classmethod
    def _matching_evidence_ids(
        cls,
        claim_tokens: set[str],
        evidence_text_by_id: dict[str, str],
    ) -> list[str]:
        scored: list[tuple[int, str]] = []
        for evidence_id, text in evidence_text_by_id.items():
            overlap_count = len(claim_tokens & cls._content_tokens(text))
            if overlap_count:
                scored.append((overlap_count, evidence_id))
        return [evidence_id for _, evidence_id in sorted(scored, reverse=True)[:4]]

    @staticmethod
    def _status(
        *,
        coverage: EvidenceCoverageReport,
        unsupported_count: int,
        partially_supported_count: int,
    ) -> AnswerQualityStatus:
        if coverage.status == CoverageStatus.insufficient:
            return AnswerQualityStatus.insufficient
        if (
            unsupported_count > 0
            or partially_supported_count > 0
            or coverage.status == CoverageStatus.partial
        ):
            return AnswerQualityStatus.partial
        return AnswerQualityStatus.strong
