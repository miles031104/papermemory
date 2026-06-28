from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, Self

from pydantic import BaseModel, Field

EvidenceSource = Literal["visrag_page", "text_page", "hybrid_page", "manual"]
EvidenceValidationState = Literal["unvalidated", "validated"]

_SAFE_PAPER_ID_PATTERN = re.compile(r"[^a-z0-9_.-]+")


def safe_paper_id(paper_id: str) -> str:
    safe = _SAFE_PAPER_ID_PATTERN.sub("-", paper_id.lower()).strip("-._")
    return safe or "paper"


def _normalized_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def deterministic_evidence_id(
    *,
    paper_id: str,
    page_number: int,
    source: EvidenceSource,
    title: str | None = None,
    caption: str | None = None,
) -> str:
    digest_input = {
        "paper_id": paper_id,
        "page_number": page_number,
        "source": source,
        "title": _normalized_text(title),
        "caption": _normalized_text(caption),
    }
    digest = hashlib.sha256(
        json.dumps(digest_input, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:8]
    return f"ev-{safe_paper_id(paper_id)}-p{page_number}-{digest}"


def deterministic_packet_id(
    *,
    query: str | None,
    paper_scope: list[str] | None,
    evidence_ids: list[str],
) -> str:
    digest_input = {
        "query": _normalized_text(query),
        "paper_scope": paper_scope,
        "evidence_ids": evidence_ids,
    }
    digest = hashlib.sha256(
        json.dumps(digest_input, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:12]
    return f"ep-{digest}"


class EvidenceRankTrace(BaseModel):
    retriever: str
    source: EvidenceSource = "visrag_page"
    rank: int | None = Field(default=None, ge=1)
    score: float | None = None


class EvidenceCitation(BaseModel):
    evidence_id: str
    paper_id: str
    page_number: int
    label: str | None = None


class EvidenceUnit(BaseModel):
    evidence_id: str
    paper_id: str
    page_number: int
    source: EvidenceSource
    score: float | None = None
    image_url: str | None = None
    title: str | None = None
    caption: str | None = None
    metadata: dict[str, str] | None = None
    rank_trace: list[EvidenceRankTrace] = Field(default_factory=list)
    validation_state: EvidenceValidationState = "unvalidated"

    @classmethod
    def from_page_evidence(
        cls,
        evidence: Any,
        *,
        rank: int | None = None,
        source: EvidenceSource = "visrag_page",
    ) -> Self:
        paper_id = str(getattr(evidence, "paper_id"))
        page_number = int(getattr(evidence, "page_number"))
        title = getattr(evidence, "title", None)
        caption = getattr(evidence, "caption", None)
        score = getattr(evidence, "score", None)
        metadata = getattr(evidence, "metadata", None)
        return cls(
            evidence_id=deterministic_evidence_id(
                paper_id=paper_id,
                page_number=page_number,
                source=source,
                title=title,
                caption=caption,
            ),
            paper_id=paper_id,
            page_number=page_number,
            source=source,
            score=float(score) if score is not None else None,
            image_url=getattr(evidence, "image_url", None),
            title=title,
            caption=caption,
            metadata=dict(metadata) if isinstance(metadata, dict) else None,
            rank_trace=[
                EvidenceRankTrace(
                    retriever="visrag",
                    source=source,
                    rank=rank,
                    score=float(score) if score is not None else None,
                )
            ],
        )


class EvidencePacket(BaseModel):
    schema_version: Literal["evidence_packet.v0"] = "evidence_packet.v0"
    packet_id: str
    query: str | None = None
    paper_scope: list[str] | None = None
    units: list[EvidenceUnit]
    citations: list[EvidenceCitation]
    limits: list[str] = Field(default_factory=list)

    @classmethod
    def from_page_evidence_list(
        cls,
        evidence: list[Any],
        *,
        query: str | None = None,
        paper_scope: list[str] | None = None,
        limits: list[str] | None = None,
    ) -> Self:
        units = [
            EvidenceUnit.from_page_evidence(item, rank=index)
            for index, item in enumerate(evidence, start=1)
        ]
        citations = [
            EvidenceCitation(
                evidence_id=unit.evidence_id,
                paper_id=unit.paper_id,
                page_number=unit.page_number,
                label=f"{unit.paper_id} p.{unit.page_number}",
            )
            for unit in units
        ]
        evidence_ids = [unit.evidence_id for unit in units]
        packet_scope = list(paper_scope) if paper_scope is not None else None
        return cls(
            packet_id=deterministic_packet_id(
                query=query,
                paper_scope=packet_scope,
                evidence_ids=evidence_ids,
            ),
            query=query,
            paper_scope=packet_scope,
            units=units,
            citations=citations,
            limits=list(limits or []),
        )
