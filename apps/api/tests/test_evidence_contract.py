import asyncio
import json
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.main import create_app
from app.routers import chat as chat_router
from app.routers import retrieval
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.evidence import EvidencePacket, EvidenceUnit
from app.schemas.retrieval import PageEvidence, RetrievalResponse
from app.services.chat_service import ChatService
from app.services.evidence_validator import (
    EvidenceValidationError,
    validate_evidence_packet,
)
from app.services.model_gateway import BuiltUserContent, GenerationResponse, ModelGateway


def test_page_evidence_adapter_generates_stable_visible_ids() -> None:
    evidence = PageEvidence(
        paper_id="paper-1-alpha",
        page_number=7,
        score=0.82,
        title="Method Overview",
        caption=r"Stored at D:\private\rendered_pages\paper\page-0007.png",
        metadata={
            "embedding_model": "openbmb/VisRAG-Ret",
            "source_path": r"C:\private\source.pdf",
        },
    )

    unit = EvidenceUnit.from_page_evidence(evidence, rank=1)
    repeated = EvidenceUnit.from_page_evidence(evidence, rank=1)

    assert unit.evidence_id == repeated.evidence_id
    assert re.match(r"^ev-paper-1-alpha-p7-[0-9a-f]{8}$", unit.evidence_id)
    assert unit.source == "visrag_page"
    assert unit.image_url == "/papers/paper-1-alpha/pages/7/image"
    assert unit.caption == "Stored at [redacted local path]"
    assert unit.metadata == {"embedding_model": "openbmb/VisRAG-Ret"}
    assert unit.rank_trace[0].retriever == "visrag"
    assert unit.rank_trace[0].rank == 1
    assert unit.validation_state == "unvalidated"


def test_packet_adapter_adds_page_citations_and_keeps_legacy_evidence_shape() -> None:
    evidence = [
        PageEvidence(
            paper_id="paper-1",
            page_number=1,
            score=0.9,
            image_path=r"C:\private\page-0001.png",
            caption="overview",
        )
    ]

    packet = EvidencePacket.from_page_evidence_list(
        evidence,
        query="What is the method?",
        paper_scope=["paper-1"],
        limits=[],
    )

    assert packet.schema_version == "evidence_packet.v0"
    assert packet.packet_id.startswith("ep-")
    assert packet.query == "What is the method?"
    assert packet.paper_scope == ["paper-1"]
    assert [unit.paper_id for unit in packet.units] == ["paper-1"]
    assert packet.citations[0].evidence_id == packet.units[0].evidence_id
    assert packet.citations[0].label == "paper-1 p.1"

    retrieval_response = RetrievalResponse(
        status="success",
        query="What is the method?",
        evidence=evidence,
        evidence_packet=packet,
        retrieval_model="fake-visrag",
        stats={"retrieval_attempted": True, "paper_scope_count": 1, "evidence_count": 1},
    )
    chat_response = ChatResponse(
        status="success",
        answer="answer",
        evidence=evidence,
        evidence_packet=packet,
        model="stub",
        prompt_preview="prompt",
        stats={
            "retrieval_attempted": True,
            "paper_scope_count": 1,
            "evidence_count": 1,
            "included_image_count": 0,
        },
    )

    retrieval_body = retrieval_response.model_dump(mode="json")
    chat_body = chat_response.model_dump(mode="json")
    assert retrieval_body["evidence"][0]["paper_id"] == "paper-1"
    assert chat_body["evidence"][0]["paper_id"] == "paper-1"
    assert "image_path" not in json.dumps(retrieval_body)
    assert "image_path" not in json.dumps(chat_body)
    assert retrieval_body["evidence_packet"]["units"][0]["paper_id"] == "paper-1"
    assert chat_body["evidence_packet"]["units"][0]["paper_id"] == "paper-1"


def test_validate_evidence_packet_rejects_duplicate_unit_ids() -> None:
    evidence = PageEvidence(paper_id="paper-1", page_number=1, score=0.9)
    unit = EvidenceUnit.from_page_evidence(evidence)
    packet = EvidencePacket(
        packet_id="ep-duplicate",
        query=None,
        paper_scope=["paper-1"],
        units=[unit, unit],
        citations=[],
        limits=[],
    )

    with pytest.raises(EvidenceValidationError, match="Duplicate evidence_id"):
        validate_evidence_packet(packet)


def test_validate_evidence_packet_rejects_invalid_scope_and_citations() -> None:
    unit = EvidenceUnit.from_page_evidence(
        PageEvidence(paper_id="paper-1", page_number=1, score=0.9)
    )
    out_of_scope_packet = EvidencePacket(
        packet_id="ep-scope",
        query=None,
        paper_scope=["paper-1"],
        units=[unit],
        citations=[],
        limits=[],
    )
    missing_citation_packet = EvidencePacket(
        packet_id="ep-missing-citation",
        query=None,
        paper_scope=["paper-1"],
        units=[unit],
        citations=[
            {
                "evidence_id": "ev-missing",
                "paper_id": "paper-1",
                "page_number": 1,
                "label": "paper-1 p.1",
            }
        ],
        limits=[],
    )
    mismatched_citation_packet = EvidencePacket(
        packet_id="ep-mismatched-citation",
        query=None,
        paper_scope=["paper-1"],
        units=[unit],
        citations=[
            {
                "evidence_id": unit.evidence_id,
                "paper_id": "paper-1",
                "page_number": 2,
                "label": "paper-1 p.2",
            }
        ],
        limits=[],
    )

    with pytest.raises(EvidenceValidationError, match="outside paper scope"):
        validate_evidence_packet(out_of_scope_packet, paper_scope=["paper-2"])
    with pytest.raises(EvidenceValidationError, match="not present"):
        validate_evidence_packet(missing_citation_packet)
    with pytest.raises(EvidenceValidationError, match="does not match"):
        validate_evidence_packet(mismatched_citation_packet)


def test_validate_evidence_packet_checks_files_and_marks_units_validated(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage")
    paths = StoragePaths(settings)
    paths.ensure_all()
    (paths.paper_dir("paper-1")).mkdir(parents=True)
    paths.paper_metadata_path("paper-1").write_text("{}", encoding="utf-8")
    paths.page_images_dir("paper-1").mkdir(parents=True)
    paths.page_image_path("paper-1", 1).write_bytes(b"\x89PNG\r\n\x1a\nfake")

    packet = EvidencePacket.from_page_evidence_list(
        [PageEvidence(paper_id="paper-1", page_number=1, score=0.9)],
        paper_scope=["paper-1"],
    )

    validated = validate_evidence_packet(
        packet,
        paths=paths,
        paper_scope=["paper-1"],
        require_files=True,
    )

    assert validated.units[0].validation_state == "validated"

    missing_packet = EvidencePacket.from_page_evidence_list(
        [PageEvidence(paper_id="paper-1", page_number=2, score=0.8)],
        paper_scope=["paper-1"],
    )
    with pytest.raises(EvidenceValidationError, match="page image"):
        validate_evidence_packet(missing_packet, paths=paths, require_files=True)


def test_validate_evidence_packet_rejects_public_local_path_leaks() -> None:
    unit = EvidenceUnit(
        evidence_id="ev-paper-1-p1-deadbeef",
        paper_id="paper-1",
        page_number=1,
        source="visrag_page",
        score=0.9,
        image_url="/papers/paper-1/pages/1/image",
        title=None,
        caption=r"leaks C:\Users\Miles CUI\private\page.png",
        metadata=None,
        rank_trace=[],
        validation_state="unvalidated",
    )
    packet = EvidencePacket(
        packet_id="ep-path-leak",
        query=None,
        paper_scope=["paper-1"],
        units=[unit],
        citations=[],
        limits=[],
    )

    with pytest.raises(EvidenceValidationError, match="local path"):
        validate_evidence_packet(packet)


def test_validate_evidence_packet_rejects_path_like_limits_without_units() -> None:
    packet = EvidencePacket(
        packet_id="ep-empty-limit-leak",
        query=None,
        paper_scope=[],
        units=[],
        citations=[],
        limits=[r"C:\secret\paper.pdf"],
    )

    with pytest.raises(EvidenceValidationError, match="limits"):
        validate_evidence_packet(packet)


class _FakeEmbedding:
    vector = [0.1, 0.2]


class _FakeVisRAG:
    model_name = "fake-visrag"

    async def embed_query(self, query: str) -> _FakeEmbedding:
        return _FakeEmbedding()


class _FakeVectorStore:
    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        return [
            PageEvidence(
                paper_id="paper-1",
                page_number=1,
                score=0.9,
                caption="contract evidence",
            )
        ]


def _write_backing_page(settings: Settings, paper_id: str, page_number: int) -> None:
    paths = StoragePaths(settings)
    paths.ensure_all()
    paths.paper_dir(paper_id).mkdir(parents=True, exist_ok=True)
    paths.paper_metadata_path(paper_id).write_text("{}", encoding="utf-8")
    paths.page_images_dir(paper_id).mkdir(parents=True, exist_ok=True)
    paths.page_image_path(paper_id, page_number).write_bytes(b"\x89PNG\r\n\x1a\nfake")


def test_retrieval_route_includes_packet_additively(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage")
    _write_backing_page(settings, "paper-1", 1)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[retrieval.get_visrag_service] = lambda: _FakeVisRAG()
    app.dependency_overrides[retrieval.get_vector_store] = lambda: _FakeVectorStore()

    response = TestClient(app).post(
        "/retrieval/search",
        json={"query": "contract?", "paper_ids": ["paper-1"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidence"][0]["paper_id"] == "paper-1"
    assert body["evidence_packet"]["query"] == "contract?"
    assert body["evidence_packet"]["paper_scope"] == ["paper-1"]
    assert body["evidence_packet"]["units"][0]["paper_id"] == "paper-1"
    assert "image_path" not in response.text


def test_retrieval_no_scope_allows_path_like_user_query_with_empty_packet() -> None:
    app = create_app()
    app.dependency_overrides[retrieval.get_visrag_service] = lambda: _FakeVisRAG()
    app.dependency_overrides[retrieval.get_vector_store] = lambda: _FakeVectorStore()

    response = TestClient(app).post(
        "/retrieval/search",
        json={"query": "where is storage/papers?", "paper_ids": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["evidence"] == []
    assert body["evidence_packet"]["query"] == "where is storage/papers?"
    assert body["evidence_packet"]["units"] == []
    assert body["limits"] == ["No paper scope selected; retrieval skipped."]


class _StreamingGateway(ModelGateway):
    async def generate_stream(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        yield "A"
        yield "nswer"

    async def generate(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> GenerationResponse:
        return GenerationResponse(text="summary", model="stub")

    def build_user_content(
        self,
        text: str,
        image_paths: list[str],
        enable_image_context: bool | None = None,
        max_evidence_images: int | None = None,
    ) -> BuiltUserContent:
        return BuiltUserContent(content=text, included_image_count=0)


def test_chat_stream_service_frames_include_packet_without_reordering() -> None:
    async def run() -> None:
        service = ChatService(
            visrag=_FakeVisRAG(),  # type: ignore[arg-type]
            vector_store=_FakeVectorStore(),  # type: ignore[arg-type]
            model_gateway=_StreamingGateway(Settings()),
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="contract?",
            paper_ids=["paper-1"],
            model="m",
            api_key="k",
            base_url="http://fake.local/v1",
        )

        chunks: list[str | dict[str, Any]] = []
        async for chunk in service.answer_stream(request):
            chunks.append(chunk)

        assert isinstance(chunks[0], dict)
        assert "evidence_ready" in chunks[0]
        assert chunks[0]["evidence_packet"].query == "contract?"
        assert chunks[1:3] == ["A", "nswer"]
        assert isinstance(chunks[-1], dict)
        assert chunks[-1]["answer"] == "Answer"
        assert chunks[-1]["evidence_packet"].query == "contract?"

    asyncio.run(run())


def test_chat_no_scope_allows_path_like_user_question_with_empty_packet() -> None:
    app = create_app()
    app.dependency_overrides[chat_router.get_chat_service] = lambda: ChatService(
        visrag=_FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=_FakeVectorStore(),  # type: ignore[arg-type]
        model_gateway=_StreamingGateway(Settings()),
        page_image_resolver=None,
    )

    response = TestClient(app).post(
        "/chat",
        json={
            "question": "where is storage/papers?",
            "paper_ids": [],
            "model": "m",
            "api_key": "k",
            "base_url": "http://fake.local/v1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["evidence"] == []
    assert body["evidence_packet"]["query"] == "where is storage/papers?"
    assert body["evidence_packet"]["units"] == []
    assert body["limits"] == [
        "No retrieved paper evidence is available; this response is not paper-grounded."
    ]
