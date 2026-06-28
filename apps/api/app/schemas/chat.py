from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent_trace import AgentTrace
from app.schemas.evidence import EvidencePacket
from app.schemas.reliability import AnswerReliabilityReport
from app.schemas.retrieval import PageEvidence


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    paper_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=25)
    # Minimum similarity score; pages below this are dropped before prompt
    # construction. None = include all top_k results (no floor).
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    # Max evidence pages allowed per paper in a multi-paper scope.
    # Prevents one paper from monopolising all top_k slots.
    # None = no per-paper cap.
    max_per_paper: int | None = Field(default=None, ge=1, le=25)
    messages: list[ChatMessage] = Field(default_factory=list)
    provider: str = "openai-compatible"
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = Field(default=None, repr=False)
    temperature: float = Field(default=0.2, ge=0, le=2)
    enable_image_context: bool | None = None
    max_evidence_images: int | None = Field(default=None, ge=0, le=10)
    retrieval_mode: Literal["visual", "hybrid"] = "hybrid"
    enable_query_rewrite: bool = False
    enable_agentic_retrieval: bool = True
    enable_reliability_layer: bool = True


class ChatStats(BaseModel):
    retrieval_attempted: bool
    paper_scope_count: int
    evidence_count: int
    included_image_count: int


class ChatResponse(BaseModel):
    status: Literal["success", "partial", "error"]
    answer: str
    evidence: list[PageEvidence]
    evidence_packet: EvidencePacket | None = None
    agent_trace: AgentTrace | None = None
    reliability_report: AnswerReliabilityReport | None = None
    model: str
    prompt_preview: str
    note: str | None = None
    stats: ChatStats
    limits: list[str] = Field(default_factory=list)
