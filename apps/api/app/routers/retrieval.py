from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.schemas.evidence import EvidencePacket
from app.schemas.retrieval import RetrievalQuery, RetrievalResponse
from app.services.evidence_validator import EvidenceValidationError, validate_evidence_packet
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.text_manifest_store import TextManifestStore
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService, VisRAGUnavailable

router = APIRouter()

NO_PAPER_SCOPE_LIMIT = "No paper scope selected; retrieval skipped."
NO_SCOPED_EVIDENCE_LIMIT = "Scoped retrieval returned no evidence."


def get_visrag_service(settings: Settings = Depends(get_settings)) -> VisRAGService:
    return VisRAGService(settings=settings)


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    return VectorStore(settings=settings)


@router.post("/search", response_model=RetrievalResponse)
async def search(
    request: RetrievalQuery,
    settings: Settings = Depends(get_settings),
    visrag: VisRAGService = Depends(get_visrag_service),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RetrievalResponse:
    paths = StoragePaths(settings)
    if request.retrieval_mode == "hybrid":
        hybrid = HybridRetrievalService(
            visrag=visrag,
            vector_store=vector_store,
            manifest_store=TextManifestStore(paths),
        )
        try:
            result = await hybrid.search(
                query=request.query,
                paper_ids=request.paper_ids,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
                max_per_paper=request.max_per_paper,
            )
        except VisRAGUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        try:
            evidence_packet = validate_evidence_packet(
                result.evidence_packet,
                paths=paths,
                paper_scope=request.paper_ids,
                require_files=True,
            )
        except EvidenceValidationError as exc:
            raise HTTPException(
                status_code=500,
                detail="Evidence packet validation failed.",
            ) from exc

        return RetrievalResponse(
            status=result.status,
            query=request.query,
            evidence=result.evidence,
            evidence_packet=evidence_packet,
            retrieval_model=f"{visrag.model_name}+bm25",
            note=None if result.evidence else "Hybrid retrieval returned no evidence.",
            stats={
                "retrieval_attempted": bool(request.paper_ids),
                "paper_scope_count": len(request.paper_ids or []),
                "evidence_count": len(result.evidence),
            },
            limits=result.limits,
        )

    if not request.paper_ids:
        limits = [NO_PAPER_SCOPE_LIMIT]
        evidence_packet = validate_evidence_packet(
            EvidencePacket.from_page_evidence_list(
                [],
                query=request.query,
                paper_scope=request.paper_ids,
                limits=limits,
            ),
            paper_scope=request.paper_ids,
        )
        return RetrievalResponse(
            status="partial",
            query=request.query,
            evidence=[],
            evidence_packet=evidence_packet,
            retrieval_model=visrag.model_name,
            note="No paper scope selected; returning no evidence.",
            stats={
                "retrieval_attempted": False,
                "paper_scope_count": 0,
                "evidence_count": 0,
            },
            limits=limits,
        )

    try:
        query_embedding = await visrag.embed_query(request.query)
    except VisRAGUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    evidence = await vector_store.search_pages(
        embedding=query_embedding.vector,
        top_k=request.top_k,
        paper_ids=request.paper_ids,
        score_threshold=request.score_threshold,
        max_per_paper=request.max_per_paper,
    )
    limits = [] if evidence else [NO_SCOPED_EVIDENCE_LIMIT]
    try:
        evidence_packet = validate_evidence_packet(
            EvidencePacket.from_page_evidence_list(
                evidence,
                query=request.query,
                paper_scope=request.paper_ids,
                limits=limits,
            ),
            paths=paths,
            paper_scope=request.paper_ids,
            require_files=True,
        )
    except EvidenceValidationError as exc:
        raise HTTPException(
            status_code=500,
            detail="Evidence packet validation failed.",
        ) from exc
    return RetrievalResponse(
        status="success" if evidence else "partial",
        query=request.query,
        evidence=evidence,
        evidence_packet=evidence_packet,
        retrieval_model=visrag.model_name,
        note=None,
        stats={
            "retrieval_attempted": True,
            "paper_scope_count": len(request.paper_ids),
            "evidence_count": len(evidence),
        },
        limits=limits,
    )
