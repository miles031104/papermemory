"""Tests for LLM query rewriting and citation verification in ChatService."""
import asyncio
from typing import Any

from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.model_gateway import GenerationResponse, ModelGateway
from app.services.visrag_service import EmbeddingResult


# ── Shared fakes ──────────────────────────────────────────────────────────────

class RecordingGateway(ModelGateway):
    """Records every generate() call and returns a canned response."""

    def __init__(self, generate_text: str = "rewritten query") -> None:
        self._generate_text = generate_text
        self.generate_calls: list[list[dict]] = []

    async def generate(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> GenerationResponse:
        self.generate_calls.append(list(messages))
        return GenerationResponse(text=self._generate_text, model="stub")

    async def generate_stream(self, messages: Any, **kwargs):
        yield "answer token"

    def build_user_content(self, text: str, image_paths, **kwargs):
        from app.services.model_gateway import BuiltUserContent
        return BuiltUserContent(content=text, included_image_count=0)


class TrackingVisRAG:
    model_name = "stub"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
        return EmbeddingResult(vector=[1.0, 0.0], model="stub", instruction="stub")


class FixedVectorStore:
    """Returns one evidence item regardless of query."""

    def __init__(self, evidence: list[PageEvidence] | None = None) -> None:
        self._evidence = evidence or [
            PageEvidence(paper_id="paper-abc", page_number=3, score=0.8, caption="x")
        ]

    async def search_pages(self, embedding, top_k, paper_ids=None,
                           score_threshold=None, max_per_paper=None):
        return list(self._evidence)


class EmptyVectorStore:
    async def search_pages(self, **kwargs):
        return []


def _two_turn_messages() -> list[ChatMessage]:
    return [
        ChatMessage(role="user", content="What is the main method?"),
        ChatMessage(role="assistant", content="The main method is X."),
    ]


def test_agentic_retrieval_runs_planned_queries_and_dedupes_top_k():
    """The planner chooses bounded search queries; backend dedupes and ranks pages."""
    async def run():
        class MultiPassStore:
            def __init__(self):
                self.calls = 0

            async def search_pages(self, embedding, top_k, paper_ids=None,
                                   score_threshold=None, max_per_paper=None):
                self.calls += 1
                if self.calls == 1:
                    return [
                        PageEvidence(paper_id="p1", page_number=2, score=0.6, caption="method"),
                        PageEvidence(paper_id="p1", page_number=3, score=0.4, caption="overview"),
                    ]
                if self.calls == 2:
                    return [
                        PageEvidence(paper_id="p1", page_number=2, score=0.9, caption="better duplicate"),
                        PageEvidence(paper_id="p1", page_number=5, score=0.7, caption="experiment"),
                    ]
                if self.calls == 3:
                    return [PageEvidence(paper_id="p1", page_number=8, score=0.8, caption="results")]
                return [PageEvidence(paper_id="p1", page_number=13, score=0.1, caption="extra")]

        gateway = RecordingGateway(
            generate_text=(
                '{"queries": ['
                '{"query": "method architecture", "target_sections": ["method"]},'
                '{"query": "experimental setup datasets baselines", "target_sections": ["experiments"]},'
                '{"query": "result metrics comparison", "target_sections": ["results"]},'
                '{"query": "limitations failure cases", "target_sections": ["limitations"]},'
                '{"query": "ignored fifth query", "target_sections": ["extra"]}'
                ']}'
            )
        )
        visrag = TrackingVisRAG()
        store = MultiPassStore()
        service = ChatService(
            visrag=visrag,
            vector_store=store,
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="How strong is the method?",
            paper_ids=["p1"],
            top_k=3,
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=_two_turn_messages(),
            enable_agentic_retrieval=True,
        )

        evidence, retrieval_attempted = await service._do_retrieval(request)

        assert retrieval_attempted is True
        assert visrag.queries == [
            "method architecture",
            "experimental setup datasets baselines",
            "result metrics comparison",
            "limitations failure cases",
        ]
        assert [(item.paper_id, item.page_number, item.score) for item in evidence] == [
            ("p1", 2, 0.9),
            ("p1", 8, 0.8),
            ("p1", 5, 0.7),
        ]
        assert len(gateway.generate_calls) == 1
        assert "retrieval planner" in gateway.generate_calls[0][0]["content"]

    asyncio.run(run())


def test_agentic_retrieval_falls_back_to_query_rewrite_on_invalid_plan():
    """Planner failure must not block retrieval; existing query rewrite remains the fallback."""
    async def run():
        gateway = RecordingGateway(generate_text="not json")
        visrag = TrackingVisRAG()
        service = ChatService(
            visrag=visrag,
            vector_store=FixedVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="how does it compare?",
            paper_ids=["paper-abc"],
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=_two_turn_messages(),
            enable_agentic_retrieval=True,
            enable_query_rewrite=True,
        )

        await service._do_retrieval(request)

        assert len(gateway.generate_calls) == 2
        assert "retrieval planner" in gateway.generate_calls[0][0]["content"]
        assert "query optimizer" in gateway.generate_calls[1][0]["content"]
        assert visrag.queries == ["not json"]

    asyncio.run(run())


# ── Query rewriting tests ─────────────────────────────────────────────────────

def test_rewrite_query_is_called_when_flag_set_and_messages_present():
    """_do_retrieval calls _rewrite_query when enable_query_rewrite=True and messages >= 2."""
    async def run():
        gateway = RecordingGateway(generate_text="how does X compare to baseline?")
        visrag = TrackingVisRAG()
        service = ChatService(
            visrag=visrag,
            vector_store=FixedVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="how does it compare?",
            paper_ids=["paper-abc"],
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=_two_turn_messages(),
            enable_query_rewrite=True,
            enable_agentic_retrieval=False,
        )

        await service._do_retrieval(request)

        # generate() called once for query rewriting
        assert len(gateway.generate_calls) == 1
        system_msgs = [m for call in gateway.generate_calls for m in call if m.get("role") == "system"]
        assert any("query optimizer" in m["content"] for m in system_msgs)

        # The embed query must be the rewritten text, not the original question
        assert visrag.queries[0] == "how does X compare to baseline?"

    asyncio.run(run())


def test_rewrite_query_not_called_when_flag_false():
    """_do_retrieval does not call generate() when enable_query_rewrite=False."""
    async def run():
        gateway = RecordingGateway()
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=FixedVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=_two_turn_messages(),
            enable_query_rewrite=False,
            enable_agentic_retrieval=False,
        )

        await service._do_retrieval(request)

        assert len(gateway.generate_calls) == 0

    asyncio.run(run())


def test_rewrite_query_not_called_when_fewer_than_two_messages():
    """_do_retrieval skips rewriting when there are fewer than 2 prior messages."""
    async def run():
        gateway = RecordingGateway()
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=FixedVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=[ChatMessage(role="user", content="hello")],  # only 1 message
            enable_query_rewrite=True,
            enable_agentic_retrieval=False,
        )

        await service._do_retrieval(request)

        assert len(gateway.generate_calls) == 0

    asyncio.run(run())


def test_rewrite_query_falls_back_to_original_on_error():
    """_rewrite_query returns the original question when the model call fails."""
    async def run():
        class FailingGateway(RecordingGateway):
            async def generate(self, messages, **kwargs):
                raise RuntimeError("model offline")

        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=FixedVectorStore(),
            model_gateway=FailingGateway(),
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=_two_turn_messages(),
            enable_query_rewrite=True,
            enable_agentic_retrieval=False,
        )

        result = await service._rewrite_query(request)
        assert result == "What is X?"

    asyncio.run(run())


def test_rewrite_query_used_as_first_embed_retry_still_uses_bare_question():
    """On zero results, the retry embed always uses the bare question, not the rewritten one."""
    async def run():
        class ZeroThenFoundStore:
            def __init__(self):
                self._calls = 0

            async def search_pages(self, embedding, top_k, paper_ids=None,
                                   score_threshold=None, max_per_paper=None):
                self._calls += 1
                if self._calls == 1:
                    return []
                return [PageEvidence(paper_id="p1", page_number=1, score=0.5, caption="retry")]

        store = ZeroThenFoundStore()
        visrag = TrackingVisRAG()
        gateway = RecordingGateway(generate_text="rewritten: limitations of method X")

        service = ChatService(
            visrag=visrag,
            vector_store=store,
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="limitations?",
            paper_ids=["p1"],
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            messages=_two_turn_messages(),
            enable_query_rewrite=True,
            enable_agentic_retrieval=False,
        )

        evidence, _ = await service._do_retrieval(request)

        assert len(evidence) == 1
        # 3 embed calls: rewrite-query result, then retry with bare question
        assert len(visrag.queries) == 2
        assert visrag.queries[0] == "rewritten: limitations of method X"
        assert visrag.queries[1] == "limitations?"  # bare question on retry

    asyncio.run(run())


# ── Citation verification tests ───────────────────────────────────────────────

def test_verify_citations_keeps_valid_citations():
    evidence = [PageEvidence(paper_id="paper-xyz", page_number=5, score=0.9, caption="c")]
    answer = "The results in paper-xyz p.5 confirm the hypothesis."
    verified, removed = ChatService._verify_citations(answer, evidence)
    assert "paper-xyz p.5" in verified
    assert removed == []


def test_verify_citations_removes_hallucinated_page():
    evidence = [PageEvidence(paper_id="paper-xyz", page_number=5, score=0.9, caption="c")]
    # page 99 is not in evidence
    answer = "See paper-xyz p.99 and paper-xyz p.5 for details."
    verified, removed = ChatService._verify_citations(answer, evidence)
    assert "paper-xyz p.99" not in verified
    assert "paper-xyz p.5" in verified
    assert removed == ["paper-xyz p.99"]


def test_verify_citations_ignores_unknown_paper_ids():
    evidence = [PageEvidence(paper_id="known-paper", page_number=1, score=0.8, caption="c")]
    # "other-paper" is not in the evidence scope — leave it alone
    answer = "See other-paper p.3 and known-paper p.1."
    verified, removed = ChatService._verify_citations(answer, evidence)
    assert "other-paper p.3" in verified   # untouched
    assert "known-paper p.1" in verified   # valid, kept
    assert removed == []


def test_verify_citations_returns_unchanged_when_no_evidence():
    answer = "Some answer with no citations."
    verified, removed = ChatService._verify_citations(answer, [])
    assert verified == answer
    assert removed == []


def test_verify_citations_cleans_double_spaces():
    evidence = [PageEvidence(paper_id="p1", page_number=2, score=0.7, caption="c")]
    # After removing the hallucinated citation, double space should be collapsed
    answer = "Results at p1 p.99 confirm this."
    verified, removed = ChatService._verify_citations(answer, evidence)
    assert "  " not in verified
    assert removed == ["p1 p.99"]


def test_answer_stream_done_frame_includes_removed_citations_in_stats():
    """done frame stats contains removed_citations list (empty when nothing is hallucinated)."""
    async def run():
        from app.services.model_gateway import BuiltUserContent

        class SimpleGateway(ModelGateway):
            def __init__(self):
                pass  # skip Settings-based __init__

            async def generate_stream(self, messages, **kwargs):
                yield "The answer"

            async def generate(self, messages, **kwargs):
                return GenerationResponse(text="summary", model="stub")

            def build_user_content(self, text, image_paths, **kwargs):
                return BuiltUserContent(content=text, included_image_count=0)

        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=SimpleGateway(),
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="Q?",
            paper_ids=None,
            base_url="http://fake/v1",
            api_key="k",
            model="m",
        )

        done = None
        async for chunk in service.answer_stream(request):
            if isinstance(chunk, dict) and "answer" in chunk:
                done = chunk

        assert done is not None
        assert "removed_citations" in done["stats"]
        assert isinstance(done["stats"]["removed_citations"], list)

    asyncio.run(run())
