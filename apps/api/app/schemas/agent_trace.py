from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.retrieval import redact_path_like_text

AgentRetrievalMode = Literal["hybrid", "visual"]
AgentState = Literal[
    "query_rewrite",
    "first_retrieval",
    "evidence_analysis",
    "coverage_check",
    "second_retrieval",
    "sufficiency_check",
    "final_retrieval",
    "answer",
]
AgentStopReason = Literal["sufficient", "insufficient_evidence", "budget_exhausted", "no_new_evidence"]

_MAX_TRACE_TEXT_CHARS = 180
_UNSAFE_TRACE_PATTERNS = (
    re.compile(r"(?i)\b(ignore|override|bypass|change)\b.{0,48}\b(system|tool|instruction|rules?)\b"),
    re.compile(r"(?i)\b(api[_ -]?keys?|secrets?|credentials?|(?:api|access|auth|bearer)[_ -]?tokens?)\b"),
    re.compile(r"(?i)\b(chain[- ]?of[- ]?thought|scratchpad|hidden reasoning)\b"),
    re.compile(r"(?i)<\s*/?\s*think\s*>"),
)
_UNSAFE_TRACE_REDACTION = "[redacted unsafe trace text]"


def sanitize_trace_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    text = redact_path_like_text(text) or ""
    if any(pattern.search(text) for pattern in _UNSAFE_TRACE_PATTERNS):
        return _UNSAFE_TRACE_REDACTION
    return text[:_MAX_TRACE_TEXT_CHARS]


def _sanitize_trace_text_list(value: Any, *, max_items: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for raw_item in value:
        if not isinstance(raw_item, str):
            continue
        item = sanitize_trace_text(raw_item)
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if max_items is not None and len(items) >= max_items:
            break
    return items


class PlannerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_queries: list[str] = Field(default_factory=list, max_length=4)
    retrieval_mode: AgentRetrievalMode = "hybrid"
    missing_evidence: list[str] = Field(default_factory=list, max_length=6)
    stop_reason: AgentStopReason | None = None
    confidence_band: Literal["low", "medium", "high"] = "medium"

    @field_validator("next_queries", mode="before")
    @classmethod
    def sanitize_next_queries(cls, value: Any) -> list[str]:
        return _sanitize_trace_text_list(value, max_items=4)

    @field_validator("missing_evidence", mode="before")
    @classmethod
    def sanitize_missing_evidence(cls, value: Any) -> list[str]:
        return _sanitize_trace_text_list(value, max_items=6)


class AgentTraceAction(BaseModel):
    state: AgentState
    pass_index: int = Field(ge=0, le=3)
    query: str | None = None
    retrieval_mode: AgentRetrievalMode | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    new_evidence_ids: list[str] = Field(default_factory=list)
    evidence_delta_count: int = Field(default=0, ge=0)
    missing_evidence: list[str] = Field(default_factory=list)
    stop_reason: AgentStopReason | None = None
    note: str | None = None

    @field_validator("query", "note", mode="before")
    @classmethod
    def sanitize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return sanitize_trace_text(str(value))

    @field_validator("missing_evidence", mode="before")
    @classmethod
    def sanitize_missing_evidence(cls, value: Any) -> list[str]:
        return _sanitize_trace_text_list(value, max_items=6)

    @field_validator("evidence_ids", "new_evidence_ids", mode="before")
    @classmethod
    def sanitize_ids(cls, value: Any) -> list[str]:
        return _sanitize_trace_text_list(value)


class AgentTrace(BaseModel):
    trace_id: str
    max_passes: int = 3
    max_queries_per_pass: int = 4
    actions: list[AgentTraceAction]
    final_stop_reason: AgentStopReason
    limits: list[str] = Field(default_factory=list)

    @field_validator("trace_id", mode="before")
    @classmethod
    def sanitize_trace_id(cls, value: Any) -> str:
        sanitized = sanitize_trace_text(str(value))
        return sanitized or "trace"

    @field_validator("limits", mode="before")
    @classmethod
    def sanitize_limits(cls, value: Any) -> list[str]:
        return _sanitize_trace_text_list(value)
