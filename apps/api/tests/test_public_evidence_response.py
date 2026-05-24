from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.routers import chat, retrieval
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
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


def _client() -> TestClient:
    api = create_app()
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: FakeVisRAG()
    api.dependency_overrides[retrieval.get_vector_store] = lambda: FakeVectorStore()
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(),  # type: ignore[arg-type]
        model_gateway=RecordingModelGateway(),
    )
    return TestClient(api)


def test_retrieval_response_hides_local_image_path() -> None:
    response = _client().post(
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


def test_chat_response_hides_local_image_path() -> None:
    response = _client().post("/chat", json={"question": "what is the method?", "paper_ids": ["paper-1"]})

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
