from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import chat, health, papers, retrieval, workspace


def create_app() -> FastAPI:
    settings = get_settings()

    api = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Local-first PaperMemory backend for ingestion, VisRAG retrieval, and BYOK chat.",
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api.include_router(health.router)
    api.include_router(papers.router, prefix="/papers", tags=["papers"])
    api.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
    api.include_router(chat.router, prefix="/chat", tags=["chat"])
    api.include_router(workspace.router, prefix="/workspace", tags=["workspace"])

    return api


app = create_app()
