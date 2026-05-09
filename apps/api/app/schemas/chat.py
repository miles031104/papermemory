from pydantic import BaseModel, Field

from app.schemas.retrieval import PageEvidence


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    paper_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=25)
    messages: list[ChatMessage] = Field(default_factory=list)
    provider: str = "openai-compatible"
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = Field(default=None, repr=False)
    temperature: float = Field(default=0.2, ge=0, le=2)


class ChatResponse(BaseModel):
    answer: str
    evidence: list[PageEvidence]
    model: str
    prompt_preview: str
    note: str | None = None
