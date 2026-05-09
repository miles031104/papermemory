from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PaperStatus(StrEnum):
    queued = "queued"
    processing = "processing"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class PaperMetadata(BaseModel):
    paper_id: str
    title: str | None = None
    filename: str
    status: PaperStatus = PaperStatus.queued
    page_count: int | None = None
    created_at: datetime


class PaperUploadResponse(BaseModel):
    paper: PaperMetadata
    message: str = "PDF accepted, rendered into local page images, and indexed for VisRAG-style retrieval."


class PaperListResponse(BaseModel):
    papers: list[PaperMetadata] = Field(default_factory=list)
