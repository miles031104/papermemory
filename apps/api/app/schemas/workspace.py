from datetime import datetime
from enum import StrEnum
import re

from pydantic import BaseModel, Field

from app.schemas.reliability import AnswerReliabilityReport


WORKSPACE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"
_WORKSPACE_ID_RE = re.compile(WORKSPACE_ID_PATTERN)


def is_safe_workspace_id(value: str) -> bool:
    return bool(_WORKSPACE_ID_RE.fullmatch(value))


class WorkspaceMessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


class WorkspaceCitation(BaseModel):
    paper_id: str
    label: str
    page: int = Field(ge=1)


class WorkspaceMessage(BaseModel):
    id: str
    role: WorkspaceMessageRole
    content: str
    citations: list[WorkspaceCitation] = Field(default_factory=list)
    reliability_report: AnswerReliabilityReport | None = None


class ResearchLibrary(BaseModel):
    id: str
    name: str
    description: str = ""
    paper_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ResearchConversation(BaseModel):
    id: str
    library_id: str
    title: str
    description: str = ""
    messages: list[WorkspaceMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PaperGroup(BaseModel):
    id: str
    library_id: str
    name: str
    description: str = ""
    paper_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WorkspaceResponse(BaseModel):
    libraries: list[ResearchLibrary] = Field(default_factory=list)
    conversations: list[ResearchConversation] = Field(default_factory=list)
    paper_groups: list[PaperGroup] = Field(default_factory=list)


class CreateLibraryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    paper_ids: list[str] = Field(default_factory=list)


class UpdateLibraryRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    paper_ids: list[str] | None = None
    group_ids: list[str] | None = None


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New research chat", min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    messages: list[WorkspaceMessage] = Field(default_factory=list)


class UpdateConversationRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    messages: list[WorkspaceMessage] | None = None


class CreatePaperGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    paper_ids: list[str] = Field(default_factory=list)


class UpdatePaperGroupRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    paper_ids: list[str] | None = None
