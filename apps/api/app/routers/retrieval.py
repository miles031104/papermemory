from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.retrieval import RetrievalQuery, RetrievalResponse
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
    visrag: VisRAGService = Depends(get_visrag_service),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RetrievalResponse:
    if not request.paper_ids:
        return RetrievalResponse(
            status="partial",
            query=request.query,
            evidence=[],
            retrieval_model=visrag.model_name,
            note="No paper scope selected; returning no evidence.",
            stats={
                "retrieval_attempted": False,
                "paper_scope_count": 0,
                "evidence_count": 0,
            },
            limits=[NO_PAPER_SCOPE_LIMIT],
        )

    try:
        query_embedding = await visrag.embed_query(request.query)
    except VisRAGUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    evidence = await vector_store.search_pages(
        embedding=query_embedding.vector,
        top_k=request.top_k,
        paper_ids=request.paper_ids,
    )
    return RetrievalResponse(
        status="success" if evidence else "partial",
        query=request.query,
        evidence=evidence,
        retrieval_model=visrag.model_name,
        note=None,
        stats={
            "retrieval_attempted": True,
            "paper_scope_count": len(request.paper_ids),
            "evidence_count": len(evidence),
        },
        limits=[] if evidence else [NO_SCOPED_EVIDENCE_LIMIT],
    )
