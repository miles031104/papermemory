import asyncio
import json as json_lib
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import Settings
from app.schemas.chat import ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.model_gateway import GenerationResponse, ModelGateway
from app.services.visrag_service import EmbeddingResult


class StreamingGateway(ModelGateway):
    """Fake gateway that streams a fixed list of tokens."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    async def generate_stream(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        for token in self._tokens:
            yield token

    def build_user_content(
        self,
        text: str,
        image_paths: list[str],
        enable_image_context: bool | None = None,
        max_evidence_images: int | None = None,
    ):
        from app.services.model_gateway import BuiltUserContent
        return BuiltUserContent(content=text, included_image_count=0)


class StubVisRAG:
    model_name = "stub"

    async def embed_query(self, query: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[1.0, 0.0], model="stub", instruction="stub")


class EmptyVectorStore:
    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        return []


def _make_chat_service(tokens: list[str]) -> ChatService:
    return ChatService(
        visrag=StubVisRAG(),
        vector_store=EmptyVectorStore(),
        model_gateway=StreamingGateway(tokens),
        page_image_resolver=None,
    )


def test_answer_stream_yields_token_strings_then_done_dict():
    """answer_stream() yields str tokens then a final dict with evidence/note/stats/answer."""
    async def run():
        service = _make_chat_service(["Hello", " world"])
        request = ChatRequest(
            question="What is this?",
            paper_ids=None,
            base_url="http://fake.local/v1",
            api_key="key",
            model="test-model",
        )

        results = []
        async for chunk in service.answer_stream(request):
            results.append(chunk)

        str_chunks = [c for c in results if isinstance(c, str)]
        done_chunks = [c for c in results if isinstance(c, dict)]

        assert str_chunks == ["Hello", " world"]
        assert len(done_chunks) == 1
        done = done_chunks[0]
        assert done["answer"] == "Hello world"
        assert "evidence" in done
        assert "note" in done
        assert "stats" in done

    asyncio.run(run())


def test_answer_stream_done_frame_has_evidence_and_stats():
    """answer_stream() done frame includes evidence list and stats dict."""
    async def run():
        service = _make_chat_service(["Answer"])
        request = ChatRequest(
            question="Q?",
            paper_ids=None,
            base_url="http://fake.local/v1",
            api_key="k",
            model="m",
        )

        done = None
        async for chunk in service.answer_stream(request):
            if isinstance(chunk, dict):
                done = chunk

        assert done is not None
        assert isinstance(done["evidence"], list)
        assert isinstance(done["stats"], dict)
        assert "evidence_count" in done["stats"]

    asyncio.run(run())


# SSE endpoint test (Task 3 — added here for grouping)
def test_chat_stream_endpoint_returns_sse_with_delta_and_done_frames():
    """POST /chat?stream=true returns SSE content with delta frames and a done frame."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.routers import chat as chat_router

    class SseStreamingGateway(ModelGateway):
        def __init__(self) -> None:
            pass

        async def generate_stream(self, messages, model=None, base_url=None, api_key=None, temperature=0.2):
            for token in ["SSE ", "token"]:
                yield token

        def build_user_content(self, text, image_paths, enable_image_context=None, max_evidence_images=None):
            from app.services.model_gateway import BuiltUserContent
            return BuiltUserContent(content=text, included_image_count=0)

    def _make_sse_chat_service() -> ChatService:
        return ChatService(
            visrag=StubVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=SseStreamingGateway(),
            page_image_resolver=None,
        )

    app = create_app()
    app.dependency_overrides[chat_router.get_chat_service] = _make_sse_chat_service

    client = TestClient(app, raise_server_exceptions=True)
    response = client.post(
        "/chat?stream=true",
        json={"question": "Test streaming?", "paper_ids": None},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    lines = [line for line in body.split("\n") if line.startswith("data:")]
    frames = [json_lib.loads(line[5:].strip()) for line in lines]

    delta_frames = [f for f in frames if f.get("type") == "delta"]
    done_frames = [f for f in frames if f.get("type") == "done"]

    assert len(delta_frames) >= 1
    assert len(done_frames) == 1
    assert "answer" in done_frames[0]
    assert "evidence" in done_frames[0]
