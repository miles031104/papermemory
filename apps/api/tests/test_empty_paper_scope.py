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
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        self.search_calls += 1
        raise AssertionError("empty paper scope should not query the vector store")


class FakeEmbedding:
    vector = [0.1, 0.2]


class EmptyEvidenceVisRAG:
    model_name = "fake-visrag"

    def __init__(self) -> None:
        self.embed_calls = 0

    async def embed_query(self, query: str) -> FakeEmbedding:
        self.embed_calls += 1
        return FakeEmbedding()


class EmptyEvidenceVectorStore:
    def __init__(self) -> None:
        self.search_calls = 0
        self.paper_ids: list[str] | None = None

    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        self.search_calls += 1
        self.paper_ids = paper_ids
        return []


class RecordingModelGateway(ModelGateway):
    def __init__(self) -> None:
        super().__init__(Settings())
        self.generate_calls = 0
        self.messages = []

    async def generate(
        self,
        messages,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> GenerationResponse:
        self.generate_calls += 1
        self.messages = messages
        return GenerationResponse(text="general conversation answer", model=model or self.model)


def test_retrieval_empty_paper_ids_returns_empty_evidence_without_full_collection_search() -> None:
    visrag = RecordingVisRAG()
    vector_store = RecordingVectorStore()
    api = create_app()
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: visrag
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store
    client = TestClient(api)

    response = client.post("/retrieval/search", json={"query": "scope?", "paper_ids": []})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["evidence"] == []
    assert body["note"] == "No paper scope selected; returning no evidence."
    assert body["stats"] == {
        "retrieval_attempted": False,
        "paper_scope_count": 0,
        "evidence_count": 0,
    }
    assert body["limits"] == ["No paper scope selected; retrieval skipped."]
    assert visrag.embed_calls == 0
    assert vector_store.search_calls == 0


def test_retrieval_omitted_paper_ids_returns_empty_evidence_without_full_collection_search() -> None:
    visrag = RecordingVisRAG()
    vector_store = RecordingVectorStore()
    api = create_app()
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: visrag
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store
    client = TestClient(api)

    response = client.post("/retrieval/search", json={"query": "scope?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["evidence"] == []
    assert body["note"] == "No paper scope selected; returning no evidence."
    assert body["stats"] == {
        "retrieval_attempted": False,
        "paper_scope_count": 0,
        "evidence_count": 0,
    }
    assert body["limits"] == ["No paper scope selected; retrieval skipped."]
    assert visrag.embed_calls == 0
    assert vector_store.search_calls == 0


def test_retrieval_scoped_zero_evidence_returns_partial_metadata() -> None:
    visrag = EmptyEvidenceVisRAG()
    vector_store = EmptyEvidenceVectorStore()
    api = create_app()
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: visrag
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store
    client = TestClient(api)

    response = client.post("/retrieval/search", json={"query": "scope?", "paper_ids": ["paper-1", "paper-2"]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["evidence"] == []
    assert body["stats"] == {
        "retrieval_attempted": True,
        "paper_scope_count": 2,
        "evidence_count": 0,
    }
    assert body["limits"] == ["Scoped retrieval returned no evidence."]
    assert visrag.embed_calls == 1
    assert vector_store.search_calls == 1
    assert vector_store.paper_ids == ["paper-1", "paper-2"]


def test_chat_empty_paper_ids_uses_conversation_mode_without_full_collection_search() -> None:
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
    body = response.json()
    assert body["status"] == "success"
    assert body["answer"] == "general conversation answer"
    assert body["evidence"] == []
    assert "conversation mode" in body["prompt_preview"]
    assert "No retrieved paper evidence is available" in body["prompt_preview"]
    assert body["note"] == "Generation request used conversation mode without retrieved paper evidence."
    assert body["stats"] == {
        "retrieval_attempted": False,
        "paper_scope_count": 0,
        "evidence_count": 0,
        "included_image_count": 0,
    }
    assert body["limits"] == [
        "No retrieved paper evidence is available; this response is not paper-grounded."
    ]
    assert visrag.embed_calls == 0
    assert vector_store.search_calls == 0
    assert model_gateway.generate_calls == 1
    assert model_gateway.messages[-1]["content"] == body["prompt_preview"]


def test_chat_omitted_paper_ids_uses_conversation_mode_without_full_collection_search() -> None:
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

    response = client.post("/chat", json={"question": "Can we discuss KG notes?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["answer"] == "general conversation answer"
    assert body["evidence"] == []
    assert "conversation mode" in body["prompt_preview"]
    assert body["stats"] == {
        "retrieval_attempted": False,
        "paper_scope_count": 0,
        "evidence_count": 0,
        "included_image_count": 0,
    }
    assert body["limits"] == [
        "No retrieved paper evidence is available; this response is not paper-grounded."
    ]
    assert visrag.embed_calls == 0
    assert vector_store.search_calls == 0
    assert model_gateway.generate_calls == 1


def test_chat_scoped_zero_evidence_returns_partial_metadata() -> None:
    visrag = EmptyEvidenceVisRAG()
    vector_store = EmptyEvidenceVectorStore()
    model_gateway = RecordingModelGateway()
    api = create_app()
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=visrag,  # type: ignore[arg-type]
        vector_store=vector_store,  # type: ignore[arg-type]
        model_gateway=model_gateway,
    )
    client = TestClient(api)

    response = client.post("/chat", json={"question": "scope?", "paper_ids": ["paper-1"]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["answer"] == "general conversation answer"
    assert body["evidence"] == []
    assert "scoped retrieval mode" in body["prompt_preview"]
    assert body["note"] == "Generation request used scoped paper retrieval, but no evidence was returned."
    assert body["stats"] == {
        "retrieval_attempted": True,
        "paper_scope_count": 1,
        "evidence_count": 0,
        "included_image_count": 0,
    }
    assert body["limits"] == [
        "Scoped retrieval returned no evidence; no paper citations are available."
    ]
    # Zero-result retry: first pass with conversational query + second pass with
    # bare question. Both return empty evidence so the model sees no grounding.
    assert visrag.embed_calls == 2
    assert vector_store.search_calls == 2
    assert model_gateway.generate_calls == 1
