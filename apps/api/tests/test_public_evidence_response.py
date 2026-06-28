import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.main import create_app
from app.routers import chat, retrieval
from app.schemas.chat import ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.evidence_validator import EvidenceValidationError
from app.services.model_gateway import GenerationResponse, ModelGateway


LOCAL_IMAGE_PATH = r"C:\Users\Miles CUI\private\page-0001.png"
LOCAL_CAPTION = r"Figure copied from D:\codex\llm_paper_assis\papermemory\storage\rendered_pages\paper-1\page-0001.png"
LOCAL_METADATA_PATH = r"/Users/miles/papers/private/source.pdf"
LOCAL_INSTRUCTION_PATH = r"Represent pages from storage/rendered_pages/paper-1/page-0001.png"


class FakeEmbedding:
    vector = [0.1, 0.2]


class FakeVisRAG:
    model_name = "fake-visrag"

    async def embed_query(self, query: str) -> FakeEmbedding:
        return FakeEmbedding()


class FakeVectorStore:
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
                image_path=LOCAL_IMAGE_PATH,
                caption=LOCAL_CAPTION,
                metadata={
                    "embedding_model": "openbmb/VisRAG-Ret",
                    "embedding_instruction": LOCAL_INSTRUCTION_PATH,
                    "source_path": LOCAL_METADATA_PATH,
                    "local_path": LOCAL_IMAGE_PATH,
                    "unknown": "do not expose",
                },
            )
        ]


class MissingPageVectorStore:
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
                paper_id="missing-paper",
                page_number=999,
                score=0.9,
            )
        ]


class RecordingModelGateway(ModelGateway):
    def __init__(self) -> None:
        super().__init__(Settings())

    async def generate(
        self,
        messages,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> GenerationResponse:
        return GenerationResponse(text="answer", model=model or self.model)


def _write_backing_page(settings: Settings, paper_id: str, page_number: int) -> None:
    paths = StoragePaths(settings)
    paths.ensure_all()
    paths.paper_dir(paper_id).mkdir(parents=True, exist_ok=True)
    paths.paper_metadata_path(paper_id).write_text("{}", encoding="utf-8")
    paths.page_images_dir(paper_id).mkdir(parents=True, exist_ok=True)
    paths.page_image_path(paper_id, page_number).write_bytes(b"\x89PNG\r\n\x1a\nfake")


def _client(tmp_path) -> TestClient:
    settings = Settings(storage_root=tmp_path / "storage")
    _write_backing_page(settings, "paper-1", 1)
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: FakeVisRAG()
    api.dependency_overrides[retrieval.get_vector_store] = lambda: FakeVectorStore()
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(),  # type: ignore[arg-type]
        model_gateway=RecordingModelGateway(),
    )
    return TestClient(api)


def test_retrieval_response_hides_local_image_path(tmp_path) -> None:
    response = _client(tmp_path).post(
        "/retrieval/search",
        json={"query": "what is the method?", "paper_ids": ["paper-1"]},
    )

    assert response.status_code == 200
    body = response.json()
    evidence = body["evidence"][0]
    assert body["status"] == "success"
    assert body["stats"] == {
        "retrieval_attempted": True,
        "paper_scope_count": 1,
        "evidence_count": 1,
    }
    assert body["limits"] == []
    assert "image_path" not in evidence
    assert evidence["image_url"] == "/papers/paper-1/pages/1/image"
    assert evidence["caption"] == "Figure copied from [redacted local path]"
    assert evidence["metadata"] == {
        "embedding_model": "openbmb/VisRAG-Ret",
        "embedding_instruction": "Represent pages from [redacted local path]",
    }
    assert LOCAL_IMAGE_PATH not in response.text
    assert LOCAL_METADATA_PATH not in response.text
    assert "source_path" not in response.text
    assert "local_path" not in response.text
    assert "unknown" not in response.text


def test_chat_response_hides_local_image_path(tmp_path) -> None:
    response = _client(tmp_path).post(
        "/chat",
        json={"question": "what is the method?", "paper_ids": ["paper-1"]},
    )

    assert response.status_code == 200
    body = response.json()
    evidence = body["evidence"][0]
    assert body["status"] == "success"
    assert body["stats"] == {
        "retrieval_attempted": True,
        "paper_scope_count": 1,
        "evidence_count": 1,
        "included_image_count": 0,
    }
    assert body["limits"] == ["Text-only evidence context; no page images were included."]
    assert "image_path" not in evidence
    assert evidence["image_url"] == "/papers/paper-1/pages/1/image"
    assert evidence["caption"] == "Figure copied from [redacted local path]"
    assert evidence["metadata"] == {
        "embedding_model": "openbmb/VisRAG-Ret",
        "embedding_instruction": "Represent pages from [redacted local path]",
    }
    assert "[redacted local path]" in body["prompt_preview"]
    assert LOCAL_IMAGE_PATH not in response.text
    assert LOCAL_CAPTION not in response.text
    assert LOCAL_METADATA_PATH not in response.text
    assert "source_path" not in response.text
    assert "local_path" not in response.text
    assert "unknown" not in response.text


def test_retrieval_route_returns_generic_500_for_missing_page_image(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path / "storage")
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: FakeVisRAG()
    api.dependency_overrides[retrieval.get_vector_store] = lambda: MissingPageVectorStore()

    response = TestClient(api, raise_server_exceptions=False).post(
        "/retrieval/search",
        json={"query": "missing visual page?", "paper_ids": ["missing-paper"]},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Evidence packet validation failed."
    assert str(tmp_path) not in response.text
    assert "Missing page image" not in response.text
    assert "Missing paper metadata" not in response.text


def test_chat_route_returns_generic_500_for_missing_page_image(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path / "storage")
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=MissingPageVectorStore(),  # type: ignore[arg-type]
        model_gateway=RecordingModelGateway(),
        storage_paths=StoragePaths(settings),
    )

    response = TestClient(api, raise_server_exceptions=False).post(
        "/chat",
        json={"question": "missing visual page?", "paper_ids": ["missing-paper"]},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Evidence packet validation failed."
    assert str(tmp_path) not in response.text
    assert "Missing page image" not in response.text
    assert "Missing paper metadata" not in response.text


def test_chat_service_with_storage_paths_rejects_missing_page_image(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path / "storage")
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=MissingPageVectorStore(),  # type: ignore[arg-type]
        model_gateway=RecordingModelGateway(),
        storage_paths=StoragePaths(settings),
    )
    request = ChatRequest(question="missing visual page?", paper_ids=["missing-paper"])

    with pytest.raises(EvidenceValidationError):
        asyncio.run(service.answer(request))
