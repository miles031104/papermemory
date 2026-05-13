from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.model_gateway import ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService, VisRAGUnavailable

router = APIRouter()


def get_chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    return ChatService(
        visrag=VisRAGService(settings=settings),
        vector_store=VectorStore(settings=settings),
        model_gateway=ModelGateway(settings=settings),
        page_image_resolver=PageImageResolver(paths=StoragePaths(settings)),
    )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)) -> ChatResponse:
    try:
        return await service.answer(request)
    except VisRAGUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
