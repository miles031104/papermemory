from datetime import datetime
from enum import StrEnum
import re

from pydantic import BaseModel, Field


PAPER_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"
_PAPER_ID_RE = re.compile(PAPER_ID_PATTERN)


def is_safe_paper_id(paper_id: str) -> bool:
    return bool(_PAPER_ID_RE.fullmatch(paper_id))


def page_image_url(paper_id: str, page_number: int) -> str | None:
    if page_number < 1 or not is_safe_paper_id(paper_id):
        return None
    return f"/papers/{paper_id}/pages/{page_number}/image"


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
