import asyncio
import json as json_lib
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException

from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.context_builder import RECENT_CONVERSATION_MESSAGE_LIMIT
from app.services.model_gateway import GenerationResponse, ModelGateway
from app.services.visrag_service import EmbeddingResult


# ── Shared fakes ──────────────────────────────────────────────────────────────

class StreamingGateway(ModelGateway):
    """Fake gateway that streams a fixed list of tokens and returns a canned summary."""

    def __init__(self, tokens: list[str], summary_text: str = "Test summary.") -> None:
        self._tokens = tokens
        self._summary_text = summary_text

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

    async def generate(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> GenerationResponse:
        return GenerationResponse(text=self._summary_text, model="stub")

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


class TrackingVisRAG:
    """VisRAG stub that records every query it receives."""

    model_name = "stub"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
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


class RetryVectorStore:
    """Returns [] on the first call, then returns real evidence on the second (retry)."""

    def __init__(self, retry_evidence: list[PageEvidence]) -> None:
        self._calls = 0
        self._retry_evidence = retry_evidence

    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        self._calls += 1
        if self._calls == 1:
            return []
        return list(self._retry_evidence)


def _make_chat_service(
    tokens: list[str],
    visrag: Any = None,
    vector_store: Any = None,
    summary_text: str = "Test summary.",
) -> ChatService:
    return ChatService(
        visrag=visrag or StubVisRAG(),
        vector_store=vector_store or EmptyVectorStore(),
        model_gateway=StreamingGateway(tokens, summary_text=summary_text),
        page_image_resolver=None,
    )


def _long_messages(n: int) -> list[ChatMessage]:
    """Build n ChatMessage objects alternating user/assistant."""
    return [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"msg-{i}")
        for i in range(n)
    ]


# ── answer_stream unit tests ───────────────────────────────────────────────────

def test_answer_stream_yields_evidence_frame_before_deltas():
    """answer_stream() first yields an evidence dict, then str tokens."""
    async def run():
        service = _make_chat_service(["Hello", " world"])
        request = ChatRequest(
            question="What is this?",
            paper_ids=None,
            base_url="http://fake.local/v1",
            api_key="key",
            model="test-model",
        )

        chunks = []
        async for chunk in service.answer_stream(request):
            chunks.append(chunk)

        assert isinstance(chunks[0], dict), "first chunk must be the evidence dict"
        assert "evidence_ready" in chunks[0], "evidence dict must have 'evidence_ready' key"
        str_chunks = [c for c in chunks[1:] if isinstance(c, str)]
        assert str_chunks == ["Hello", " world"]

    asyncio.run(run())


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
        done_chunks = [c for c in results if isinstance(c, dict) and "answer" in c]

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
            if isinstance(chunk, dict) and "answer" in chunk:
                done = chunk

        assert done is not None
        assert isinstance(done["evidence"], list)
        assert isinstance(done["stats"], dict)
        assert "evidence_count" in done["stats"]

    asyncio.run(run())


def test_answer_stream_no_summary_when_messages_within_limit():
    """done frame has summary_message=None when messages <= RECENT_CONVERSATION_MESSAGE_LIMIT."""
    async def run():
        service = _make_chat_service(["ok"])
        short_messages = _long_messages(RECENT_CONVERSATION_MESSAGE_LIMIT)
        request = ChatRequest(
            question="Q?",
            paper_ids=None,
            base_url="http://fake.local/v1",
            api_key="k",
            model="m",
            messages=short_messages,
        )

        done = None
        async for chunk in service.answer_stream(request):
            if isinstance(chunk, dict) and "answer" in chunk:
                done = chunk

        assert done is not None
        assert done.get("summary_message") is None

    asyncio.run(run())


def test_answer_stream_produces_summary_when_messages_exceed_limit():
    """done frame has a summary_message dict when history is longer than the context window."""
    async def run():
        service = _make_chat_service(["answer"], summary_text="Key findings: X.")
        long_messages = _long_messages(RECENT_CONVERSATION_MESSAGE_LIMIT + 2)
        request = ChatRequest(
            question="Q?",
            paper_ids=None,
            base_url="http://fake.local/v1",
            api_key="k",
            model="m",
            messages=long_messages,
        )

        done = None
        async for chunk in service.answer_stream(request):
            if isinstance(chunk, dict) and "answer" in chunk:
                done = chunk

        assert done is not None
        sm = done.get("summary_message")
        assert sm is not None, "expected summary_message in done frame"
        assert sm["role"] == "assistant"
        assert sm["content"].startswith("[Summary]")
        assert "Key findings: X." in sm["content"]

    asyncio.run(run())


def test_answer_stream_no_re_summarization_when_summary_exists():
    """No new summary is generated when messages already start with a [Summary] message."""
    async def run():
        service = _make_chat_service(["answer"])
        messages = [
            ChatMessage(role="assistant", content="[Summary] Earlier context here."),
            *_long_messages(RECENT_CONVERSATION_MESSAGE_LIMIT + 1),
        ]
        request = ChatRequest(
            question="Q?",
            paper_ids=None,
            base_url="http://fake.local/v1",
            api_key="k",
            model="m",
            messages=messages,
        )

        done = None
        async for chunk in service.answer_stream(request):
            if isinstance(chunk, dict) and "answer" in chunk:
                done = chunk

        assert done is not None
        assert done.get("summary_message") is None

    asyncio.run(run())


def test_do_retrieval_retries_with_bare_question_on_empty_first_pass():
    """_do_retrieval() embeds twice: first with conversational context, then bare question."""
    async def run():
        retry_evidence = [
            PageEvidence(paper_id="p1", page_number=1, score=0.5, caption="found on retry")
        ]
        tracking_visrag = TrackingVisRAG()
        retry_store = RetryVectorStore(retry_evidence)
        service = ChatService(
            visrag=tracking_visrag,
            vector_store=retry_store,
            model_gateway=StreamingGateway(["ok"]),
            page_image_resolver=None,
        )

        request = ChatRequest(
            question="What is X?",
            paper_ids=["p1"],
            base_url="http://fake.local/v1",
            api_key="k",
            model="m",
            messages=[ChatMessage(role="user", content="prior question")],
        )

        evidence, retrieval_attempted = await service._do_retrieval(request)

        assert retrieval_attempted is True
        assert len(evidence) == 1
        assert evidence[0].paper_id == "p1"
        # Two embed calls: first with enriched query, second with bare question
        assert len(tracking_visrag.queries) == 2
        # The second query must be the bare question (no conversational prefix)
        assert tracking_visrag.queries[1] == "What is X?"

    asyncio.run(run())


def test_do_retrieval_single_embed_when_first_pass_returns_results():
    """_do_retrieval() only embeds once when the first pass already returns evidence."""
    async def run():
        class AlwaysFoundStore:
            async def search_pages(self, embedding, top_k, paper_ids=None,
                                   score_threshold=None, max_per_paper=None):
                return [PageEvidence(paper_id="p1", page_number=1, score=0.9, caption="x")]

        tracking_visrag = TrackingVisRAG()
        service = ChatService(
            visrag=tracking_visrag,
            vector_store=AlwaysFoundStore(),
            model_gateway=StreamingGateway(["ok"]),
            page_image_resolver=None,
        )

        request = ChatRequest(
            question="Q?", paper_ids=["p1"],
            base_url="http://fake.local/v1", api_key="k", model="m",
        )

        evidence, _ = await service._do_retrieval(request)

        assert len(evidence) == 1
        assert len(tracking_visrag.queries) == 1  # no retry

    asyncio.run(run())


# ── SSE endpoint integration test ─────────────────────────────────────────────

def test_chat_stream_endpoint_returns_sse_with_evidence_delta_and_done_frames():
    """POST /chat?stream=true returns SSE with evidence, delta, and done frames in order."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.routers import chat as chat_router

    class SseStreamingGateway(StreamingGateway):
        def __init__(self) -> None:
            super().__init__(tokens=["SSE ", "token"])

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

    evidence_frames = [f for f in frames if f.get("type") == "evidence"]
    delta_frames = [f for f in frames if f.get("type") == "delta"]
    done_frames = [f for f in frames if f.get("type") == "done"]

    assert len(evidence_frames) == 1, "expected exactly one evidence frame"
    assert len(delta_frames) >= 1
    assert len(done_frames) == 1
    assert "answer" in done_frames[0]
    assert "evidence" in done_frames[0]

    # evidence frame must arrive before any delta
    frame_types = [f["type"] for f in frames]
    evidence_idx = frame_types.index("evidence")
    first_delta_idx = frame_types.index("delta")
    assert evidence_idx < first_delta_idx, "evidence frame must precede delta frames"


def test_chat_stream_endpoint_returns_error_frame_for_provider_failure():
    """Streaming provider errors should be sent as SSE, not dropped by closing the socket."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.routers import chat as chat_router

    class FailingStreamingGateway(StreamingGateway):
        async def generate_stream(
            self,
            messages: Any,
            model: str | None = None,
            base_url: str | None = None,
            api_key: str | None = None,
            temperature: float = 0.2,
        ) -> AsyncGenerator[str, None]:
            raise HTTPException(status_code=502, detail="Model provider error: request failed: ConnectError")
            yield ""

    def _make_sse_chat_service() -> ChatService:
        return ChatService(
            visrag=StubVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=FailingStreamingGateway(tokens=[]),
            page_image_resolver=None,
        )

    app = create_app()
    app.dependency_overrides[chat_router.get_chat_service] = _make_sse_chat_service

    client = TestClient(app, raise_server_exceptions=True)
    response = client.post(
        "/chat?stream=true",
        json={"question": "Test provider failure?", "paper_ids": None},
    )

    assert response.status_code == 200
    frames = [
        json_lib.loads(line[5:].strip())
        for line in response.text.split("\n")
        if line.startswith("data:")
    ]

    assert frames[-1]["type"] == "error"
    assert frames[-1]["status"] == 502
    assert frames[-1]["detail"] == "Model provider error: request failed: ConnectError"
