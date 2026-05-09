from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.retrieval import RetrievalQuery, RetrievalResponse
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService, VisRAGUnavailable

router = APIRouter()


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
        query=request.query,
        evidence=evidence,
        retrieval_model=visrag.model_name,
        note=None,
    )
