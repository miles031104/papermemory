from __future__ import annotations

from dataclasses import dataclass

from app.schemas.evidence import (
    EvidenceCitation,
    EvidencePacket,
    EvidenceRankTrace,
    EvidenceUnit,
    deterministic_evidence_id,
    deterministic_packet_id,
)
from app.schemas.retrieval import PageEvidence
from app.services.text_retriever import TextSearchHit


@dataclass
class PageCandidate:
    paper_id: str
    page_number: int
    visual: PageEvidence | None = None
    visual_rank: int | None = None
    text: TextSearchHit | None = None
    text_rank: int | None = None
    rrf_score: float = 0.0


def fuse_page_candidates(
    *,
    visual_hits: list[PageEvidence],
    text_hits: list[TextSearchHit],
    top_k: int,
    rrf_k: int = 60,
    max_per_paper: int | None = None,
) -> list[PageCandidate]:
    candidates: dict[tuple[str, int], PageCandidate] = {}

    for rank, hit in enumerate(visual_hits, start=1):
        candidate = _candidate_for(candidates, hit.paper_id, hit.page_number)
        if candidate.visual_rank is None or rank < candidate.visual_rank:
            candidate.visual = hit
            candidate.visual_rank = rank

    for hit in text_hits:
        candidate = _candidate_for(candidates, hit.paper_id, hit.page_number)
        if candidate.text_rank is None or hit.rank < candidate.text_rank:
            candidate.text = hit
            candidate.text_rank = hit.rank

    for candidate in candidates.values():
        candidate.rrf_score = _rrf_score(
            ranks=[candidate.visual_rank, candidate.text_rank],
            rrf_k=rrf_k,
        )

    ordered = sorted(
        candidates.values(),
        key=lambda item: (-item.rrf_score, item.paper_id, item.page_number),
    )
    if max_per_paper is not None:
        ordered = _apply_max_per_paper(ordered, max_per_paper)
    return ordered[:top_k]


def build_hybrid_evidence(
    *,
    candidates: list[PageCandidate],
    query: str | None,
    paper_scope: list[str] | None,
    limits: list[str],
    rrf_k: int = 60,
) -> tuple[list[PageEvidence], EvidencePacket]:
    evidence = [_candidate_to_page_evidence(candidate) for candidate in candidates]
    units = [
        _candidate_to_evidence_unit(candidate, evidence_item=evidence_item, rrf_k=rrf_k)
        for candidate, evidence_item in zip(candidates, evidence, strict=True)
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
    packet = EvidencePacket(
        packet_id=deterministic_packet_id(
            query=query,
            paper_scope=packet_scope,
            evidence_ids=evidence_ids,
        ),
        query=query,
        paper_scope=packet_scope,
        units=units,
        citations=citations,
        limits=list(limits),
    )
    return evidence, packet


def _candidate_for(
    candidates: dict[tuple[str, int], PageCandidate],
    paper_id: str,
    page_number: int,
) -> PageCandidate:
    key = (paper_id, page_number)
    if key not in candidates:
        candidates[key] = PageCandidate(paper_id=paper_id, page_number=page_number)
    return candidates[key]


def _rrf_score(*, ranks: list[int | None], rrf_k: int) -> float:
    return sum(1.0 / (rrf_k + rank) for rank in ranks if rank is not None)


def _apply_max_per_paper(
    candidates: list[PageCandidate],
    max_per_paper: int,
) -> list[PageCandidate]:
    per_paper_count: dict[str, int] = {}
    filtered: list[PageCandidate] = []
    for candidate in candidates:
        count = per_paper_count.get(candidate.paper_id, 0)
        if count >= max_per_paper:
            continue
        filtered.append(candidate)
        per_paper_count[candidate.paper_id] = count + 1
    return filtered


def _candidate_to_page_evidence(candidate: PageCandidate) -> PageEvidence:
    caption = (
        candidate.text.snippet
        if candidate.text is not None and candidate.text.snippet
        else candidate.visual.caption
        if candidate.visual is not None
        else None
    )
    title = candidate.visual.title if candidate.visual is not None else None
    return PageEvidence(
        paper_id=candidate.paper_id,
        page_number=candidate.page_number,
        score=candidate.rrf_score,
        image_url=candidate.visual.image_url if candidate.visual is not None else None,
        title=title,
        caption=caption,
        metadata=_candidate_metadata(candidate),
    )


def _candidate_metadata(candidate: PageCandidate) -> dict[str, str] | None:
    metadata: dict[str, str] = {}
    if candidate.visual is not None and candidate.visual.metadata:
        metadata.update(candidate.visual.metadata)
    if candidate.text is not None:
        if candidate.text.quality_label is not None:
            metadata["quality_label"] = candidate.text.quality_label
            metadata["text_quality"] = candidate.text.quality_label
        if candidate.text.ocr_needed is not None:
            metadata["ocr_needed"] = str(candidate.text.ocr_needed).lower()
        if candidate.text.char_count is not None:
            metadata["char_count"] = str(candidate.text.char_count)
        if candidate.text.word_count is not None:
            metadata["word_count"] = str(candidate.text.word_count)
    return metadata or None


def _candidate_to_evidence_unit(
    candidate: PageCandidate,
    *,
    evidence_item: PageEvidence,
    rrf_k: int,
) -> EvidenceUnit:
    rank_trace: list[EvidenceRankTrace] = []
    metadata = _candidate_metadata(candidate) or {}
    metadata["rrf_k"] = str(rrf_k)
    if candidate.visual is not None:
        rank_trace.append(
            EvidenceRankTrace(
                retriever="visrag",
                source="visrag_page",
                rank=candidate.visual_rank,
                score=float(candidate.visual.score),
            )
        )
        metadata["visrag_rank"] = str(candidate.visual_rank)
        metadata["visrag_score"] = f"{float(candidate.visual.score):.12g}"
    if candidate.text is not None:
        rank_trace.append(
            EvidenceRankTrace(
                retriever="bm25",
                source="text_page",
                rank=candidate.text_rank,
                score=float(candidate.text.score),
            )
        )
        metadata["bm25_rank"] = str(candidate.text_rank)
        metadata["bm25_score"] = f"{float(candidate.text.score):.12g}"

    return EvidenceUnit(
        evidence_id=deterministic_evidence_id(
            paper_id=evidence_item.paper_id,
            page_number=evidence_item.page_number,
            source="hybrid_page",
            title=evidence_item.title,
            caption=evidence_item.caption,
        ),
        paper_id=evidence_item.paper_id,
        page_number=evidence_item.page_number,
        source="hybrid_page",
        score=candidate.rrf_score,
        image_url=evidence_item.image_url,
        title=evidence_item.title,
        caption=evidence_item.caption,
        metadata=metadata,
        rank_trace=rank_trace,
    )
