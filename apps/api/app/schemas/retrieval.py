import re
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.papers import page_image_url

PUBLIC_METADATA_KEYS = {"embedding_model", "embedding_instruction"}
PATH_REDACTION = "[redacted local path]"
PATH_LIKE_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/][^\r\n\t\"'<>|]+"),
    re.compile(r"/(?:Users|home)/[^\r\n\t\"'<>|]+"),
    re.compile(r"(?i)(?:^|(?<=\s))(?:\.?[\\/])?(?:storage|\.papermemory)[\\/][^\r\n\t\"'<>|]+"),
    re.compile(r"(?i)(?:^|(?<=\s))\S*rendered_pages[\\/]\S+"),
)


def redact_path_like_text(value: str | None) -> str | None:
    if value is None:
        return None

    redacted = value
    for pattern in PATH_LIKE_PATTERNS:
        redacted = pattern.sub(PATH_REDACTION, redacted)
    return redacted


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1)
    paper_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=25)


class PageEvidence(BaseModel):
    paper_id: str
    page_number: int
    score: float
    image_path: str | None = Field(default=None, exclude=True)
    image_url: str | None = None
    title: str | None = None
    caption: str | None = None
    metadata: dict[str, str] | None = None

    @field_validator("title", "caption", mode="before")
    @classmethod
    def redact_public_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return redact_path_like_text(str(value))

    @field_validator("metadata", mode="before")
    @classmethod
    def allow_public_metadata(cls, value: Any) -> dict[str, str] | None:
        if not isinstance(value, dict):
            return None

        metadata = {
            key: redacted
            for key, raw_value in value.items()
            if key in PUBLIC_METADATA_KEYS
            if (redacted := redact_path_like_text(str(raw_value))) is not None
        }
        return metadata or None

    @model_validator(mode="after")
    def fill_page_image_url(self) -> "PageEvidence":
        if self.image_url is None:
            self.image_url = page_image_url(self.paper_id, self.page_number)
        return self


class RetrievalStats(BaseModel):
    retrieval_attempted: bool
    paper_scope_count: int
    evidence_count: int


class RetrievalResponse(BaseModel):
    status: Literal["success", "partial", "error"]
    query: str
    evidence: list[PageEvidence]
    retrieval_model: str
    note: str | None = None
    stats: RetrievalStats
    limits: list[str] = Field(default_factory=list)
