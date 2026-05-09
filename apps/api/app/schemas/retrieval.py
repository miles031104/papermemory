from pydantic import BaseModel, Field


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1)
    paper_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=25)


class PageEvidence(BaseModel):
    paper_id: str
    page_number: int
    score: float
    image_path: str | None = None
    title: str | None = None
    caption: str | None = None
    metadata: dict[str, str] | None = None


class RetrievalResponse(BaseModel):
    query: str
    evidence: list[PageEvidence]
    retrieval_model: str
    note: str | None = None
