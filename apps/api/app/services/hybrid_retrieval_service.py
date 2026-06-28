from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidencePacket
from app.schemas.retrieval import PageEvidence
from app.services.evidence_resolver import build_hybrid_evidence, fuse_page_candidates
from app.services.evidence_validator import validate_evidence_packet
from app.services.text_manifest_store import TextManifestStore
from app.services.text_retriever import TextRetriever, TextSearchHit
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService


NO_PAPER_SCOPE_LIMIT = "No paper scope selected; retrieval skipped."
MISSING_TEXT_MANIFEST_LIMIT = "Text manifest missing for one or more scoped papers."
NO_HYBRID_EVIDENCE_LIMIT = "Hybrid retrieval returned no evidence."


class HybridRetrievalResult(BaseModel):
    status: Literal["success", "partial"]
    evidence: list[PageEvidence]
    evidence_packet: EvidencePacket
    limits: list[str] = Field(default_factory=list)
    stats: dict[str, int | float] = Field(default_factory=dict)


class HybridRetrievalService:
    def __init__(
        self,
        *,
        visrag: VisRAGService,
        vector_store: VectorStore,
        manifest_store: TextManifestStore,
        rrf_k: int = 60,
    ) -> None:
        self.visrag = visrag
        self.vector_store = vector_store
        self.manifest_store = manifest_store
        self.rrf_k = rrf_k

    async def search(
        self,
        *,
        query: str,
        paper_ids: list[str] | None,
        top_k: int,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> HybridRetrievalResult:
        if not paper_ids:
            packet = validate_evidence_packet(
                EvidencePacket.from_page_evidence_list(
                    [],
                    query=query,
                    paper_scope=paper_ids,
                    limits=[NO_PAPER_SCOPE_LIMIT],
                ),
                paper_scope=paper_ids,
            )
            return HybridRetrievalResult(
                status="partial",
                evidence=[],
                evidence_packet=packet,
                limits=[NO_PAPER_SCOPE_LIMIT],
                stats={
                    "visual_hit_count": 0,
                    "text_hit_count": 0,
                    "fused_page_count": 0,
                    "rrf_k": self.rrf_k,
                },
            )

        query_embedding = await self.visrag.embed_query(query)
        visual_hits = await self.vector_store.search_pages(
            embedding=query_embedding.vector,
            top_k=top_k,
            paper_ids=paper_ids,
            score_threshold=score_threshold,
            max_per_paper=None,
        )
        limits: list[str] = []
        text_hits = self._search_text(query=query, paper_ids=paper_ids, top_k=top_k, limits=limits)
        candidates = fuse_page_candidates(
            visual_hits=visual_hits,
            text_hits=text_hits,
            top_k=top_k,
            rrf_k=self.rrf_k,
            max_per_paper=max_per_paper,
        )
        if not candidates:
            limits.append(NO_HYBRID_EVIDENCE_LIMIT)

        evidence, packet = build_hybrid_evidence(
            candidates=candidates,
            query=query,
            paper_scope=paper_ids,
            limits=limits,
            rrf_k=self.rrf_k,
        )
        validated_packet = validate_evidence_packet(packet, paper_scope=paper_ids)
        return HybridRetrievalResult(
            status="success" if evidence else "partial",
            evidence=evidence,
            evidence_packet=validated_packet,
            limits=limits,
            stats={
                "visual_hit_count": len(visual_hits),
                "text_hit_count": len(text_hits),
                "fused_page_count": len(evidence),
                "rrf_k": self.rrf_k,
            },
        )

    def _search_text(
        self,
        *,
        query: str,
        paper_ids: list[str],
        top_k: int,
        limits: list[str],
    ) -> list[TextSearchHit]:
        manifests = []
        missing_manifest = False
        for paper_id in paper_ids:
            try:
                manifests.append(self.manifest_store.load(paper_id))
            except (FileNotFoundError, OSError, ValueError):
                missing_manifest = True

        if missing_manifest:
            limits.append(MISSING_TEXT_MANIFEST_LIMIT)
        if not manifests:
            return []

        retriever = TextRetriever.from_manifests(manifests)
        return retriever.search(query, paper_ids=paper_ids, top_k=top_k)
