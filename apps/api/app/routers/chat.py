import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

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


async def _sse_stream(service: ChatService, request: ChatRequest):
    """Async generator that yields SSE-formatted strings."""
    async for chunk in service.answer_stream(request):
        if isinstance(chunk, str):
            payload = json.dumps({"type": "delta", "content": chunk})
        else:
            payload = json.dumps({"type": "done", **chunk}, default=str)
        yield f"data: {payload}\n\n"


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    stream: Annotated[bool, Query()] = False,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse | StreamingResponse:
    try:
        if stream:
            return StreamingResponse(
                _sse_stream(service, request),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return await service.answer(request)
    except VisRAGUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
