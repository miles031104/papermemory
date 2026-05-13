from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.routers import chat, retrieval
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.model_gateway import GenerationResponse, ModelGateway


class RecordingVisRAG:
    model_name = "fake-visrag"

    def __init__(self) -> None:
        self.embed_calls = 0

    async def embed_query(self, query: str):
        self.embed_calls += 1
        raise AssertionError("empty paper scope should not embed the query")


class RecordingVectorStore:
    def __init__(self) -> None:
        self.search_calls = 0

    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
    ) -> list[PageEvidence]:
        self.search_calls += 1
        raise AssertionError("empty paper scope should not query the vector store")


class RecordingModelGateway(ModelGateway):
    def __init__(self) -> None:
        super().__init__(Settings())
        self.generate_calls = 0

    async def generate(
        self,
        messages,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> GenerationResponse:
        self.generate_calls += 1
        raise AssertionError("empty paper scope should not call the model gateway")


def test_retrieval_empty_paper_ids_returns_empty_evidence_without_full_collection_search() -> None:
    visrag = RecordingVisRAG()
    vector_store = RecordingVectorStore()
    api = create_app()
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: visrag
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store
    client = TestClient(api)

    response = client.post("/retrieval/search", json={"query": "scope?", "paper_ids": []})

    assert response.status_code == 200
    assert response.json()["evidence"] == []
    assert response.json()["note"] == "No paper scope selected; returning no evidence."
    assert visrag.embed_calls == 0
    assert vector_store.search_calls == 0


def test_chat_empty_paper_ids_returns_empty_evidence_without_full_collection_search() -> None:
    visrag = RecordingVisRAG()
    vector_store = RecordingVectorStore()
    model_gateway = RecordingModelGateway()
    api = create_app()
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=visrag,  # type: ignore[arg-type]
        vector_store=vector_store,  # type: ignore[arg-type]
        model_gateway=model_gateway,
    )
    client = TestClient(api)

    response = client.post("/chat", json={"question": "scope?", "paper_ids": []})

    assert response.status_code == 200
    assert "did not call the external model provider" in response.json()["answer"]
    assert response.json()["evidence"] == []
    assert "No retrieved page evidence yet." in response.json()["prompt_preview"]
    assert response.json()["note"] == "No paper scope selected; BYOK generation was skipped."
    assert visrag.embed_calls == 0
    assert vector_store.search_calls == 0
    assert model_gateway.generate_calls == 0
