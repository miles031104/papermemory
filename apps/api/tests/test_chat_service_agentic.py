"""Tests for LLM query rewriting and citation verification in ChatService."""
import asyncio
from typing import Any

from app.schemas.agent_trace import AgentTrace, AgentTraceAction
from app.schemas.evidence import EvidenceCitation, EvidencePacket, EvidenceRankTrace, EvidenceUnit
from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService, WEAK_EVIDENCE_LIMIT
from app.services.hybrid_retrieval_service import HybridRetrievalResult
from app.services.model_gateway import BuiltUserContent, GenerationResponse, ModelGateway
from app.services.research_orchestrator import OrchestratorResult
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
        return BuiltUserContent(content=text, included_image_count=0)


class RecordingUserContentGateway(RecordingGateway):
    def __init__(self, generate_text: str = "rewritten query") -> None:
        super().__init__(generate_text=generate_text)
        self.user_content_calls: list[dict[str, Any]] = []

    def build_user_content(self, text: str, image_paths, **kwargs):
        self.user_content_calls.append(
            {
                "text": text,
                "image_paths": list(image_paths),
                **kwargs,
            }
        )
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


class RecordingHybridRetrievalService:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def search(self, **kwargs) -> HybridRetrievalResult:
        self.calls.append(kwargs)
        return self.result


class RecordingOrchestrator:
    def __init__(self, result: OrchestratorResult) -> None:
        self.result = result
        self.requests: list[Any] = []

    async def run(self, request) -> OrchestratorResult:
        self.requests.append(request)
        return self.result


def _hybrid_result() -> HybridRetrievalResult:
    evidence = [
        PageEvidence(
            paper_id="paper-abc",
            page_number=3,
            score=0.03278688524590164,
            caption="Hybrid evidence caption.",
        )
    ]
    unit = EvidenceUnit(
        evidence_id="ev-paper-abc-p3-hybrid",
        paper_id="paper-abc",
        page_number=3,
        source="hybrid_page",
        score=evidence[0].score,
        image_url="/papers/paper-abc/pages/3/image",
        caption=evidence[0].caption,
        rank_trace=[
            EvidenceRankTrace(retriever="visrag", source="visrag_page", rank=3, score=0.72),
            EvidenceRankTrace(retriever="bm25", source="text_page", rank=1, score=9.25),
        ],
        validation_state="validated",
    )
    packet = EvidencePacket(
        packet_id="ep-agentic-hybrid",
        query="What is X?",
        paper_scope=["paper-abc"],
        units=[unit],
        citations=[
            EvidenceCitation(
                evidence_id=unit.evidence_id,
                paper_id="paper-abc",
                page_number=3,
                label="paper-abc p.3",
            )
        ],
        limits=["Text manifest missing for one or more scoped papers."],
    )
    return HybridRetrievalResult(
        status="success",
        evidence=evidence,
        evidence_packet=packet,
        limits=list(packet.limits),
    )


def _orchestrator_result() -> OrchestratorResult:
    hybrid = _hybrid_result()
    trace = AgentTrace(
        trace_id="trace-test",
        actions=[
            AgentTraceAction(
                state="first_retrieval",
                pass_index=1,
                query="What is X?",
                retrieval_mode="hybrid",
                evidence_ids=["ev-paper-abc-p3-hybrid"],
                new_evidence_ids=["ev-paper-abc-p3-hybrid"],
                evidence_delta_count=1,
            ),
            AgentTraceAction(
                state="answer",
                pass_index=1,
                evidence_ids=["ev-paper-abc-p3-hybrid"],
                stop_reason="sufficient",
            ),
        ],
        final_stop_reason="sufficient",
        limits=["max_passes=3", "max_queries_per_pass=4", "max_final_evidence_units=8"],
    )
    return OrchestratorResult(
        evidence=hybrid.evidence,
        evidence_packet=hybrid.evidence_packet,
        agent_trace=trace,
        limits=list(hybrid.limits),
    )


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


def test_scoped_hybrid_chat_uses_orchestrator_and_returns_trace_safe_actions():
    async def run():
        gateway = RecordingGateway(generate_text="Answer with paper-abc p.3.")
        hybrid = RecordingHybridRetrievalService(_hybrid_result())
        orchestrator = RecordingOrchestrator(_orchestrator_result())
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
            hybrid_retrieval=hybrid,
            research_orchestrator_factory=lambda **kwargs: orchestrator,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            retrieval_mode="hybrid",
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            enable_agentic_retrieval=True,
        )

        response = await service.answer(request)

        assert hybrid.calls == []
        assert len(orchestrator.requests) == 1
        assert orchestrator.requests[0].question == "What is X?"
        assert response.agent_trace is not None
        assert response.agent_trace.final_stop_reason == "sufficient"
        trace_text = response.agent_trace.model_dump_json()
        assert "C:\\Users" not in trace_text
        assert "ignore previous" not in trace_text.lower()
        assert "paper-abc p.3" in response.answer

    asyncio.run(run())


def test_hybrid_chat_agentic_disabled_uses_hybrid_service_and_packet_prompt_context():
    async def run():
        gateway = RecordingGateway(generate_text="Answer with paper-abc p.3 and paper-abc p.99.")
        hybrid = RecordingHybridRetrievalService(_hybrid_result())
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
            hybrid_retrieval=hybrid,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            retrieval_mode="hybrid",
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            enable_agentic_retrieval=False,
        )

        response = await service.answer(request)

        assert hybrid.calls == [
            {
                "query": "What is X?",
                "paper_ids": ["paper-abc"],
                "top_k": 5,
                "score_threshold": None,
                "max_per_paper": None,
            }
        ]
        assert response.evidence_packet is not None
        assert response.evidence_packet.packet_id == "ep-agentic-hybrid"
        assert response.agent_trace is None
        assert [trace.retriever for trace in response.evidence_packet.units[0].rank_trace] == [
            "visrag",
            "bm25",
        ]
        assert "evidence_id=ev-paper-abc-p3-hybrid" in response.prompt_preview
        assert "rank_trace=visrag r3 score=0.7200; bm25 r1 score=9.2500" in response.prompt_preview
        assert "Text manifest missing for one or more scoped papers." in response.prompt_preview
        assert "paper-abc p.3" in response.answer
        assert "paper-abc p.99" not in response.answer

    asyncio.run(run())


def test_hybrid_chat_marks_all_low_scored_evidence_as_weak():
    async def run():
        gateway = RecordingGateway(generate_text="Answer with paper-abc p.3.")
        hybrid = RecordingHybridRetrievalService(_hybrid_result())
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
            hybrid_retrieval=hybrid,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            retrieval_mode="hybrid",
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            enable_agentic_retrieval=False,
        )

        response = await service.answer(request)

        assert WEAK_EVIDENCE_LIMIT in response.limits
        assert response.evidence_packet is not None
        assert WEAK_EVIDENCE_LIMIT in response.evidence_packet.limits

    asyncio.run(run())


def test_packet_quality_limits_keep_mixed_strength_scores_unflagged():
    weak_unit = EvidenceUnit(
        evidence_id="ev-p1-p1-weak",
        paper_id="p1",
        page_number=1,
        source="hybrid_page",
        score=0.03,
        validation_state="validated",
    )
    strong_unit = EvidenceUnit(
        evidence_id="ev-p1-p2-strong",
        paper_id="p1",
        page_number=2,
        source="hybrid_page",
        score=0.72,
        validation_state="validated",
    )
    packet = EvidencePacket(
        packet_id="ep-mixed-strength",
        query="Q?",
        paper_scope=["p1"],
        units=[weak_unit, strong_unit],
        citations=[],
    )

    limits = ChatService._packet_quality_limits(packet)

    assert WEAK_EVIDENCE_LIMIT not in limits


def test_packet_quality_limits_ignore_units_without_scores_for_weak_limit():
    unit = EvidenceUnit(
        evidence_id="ev-p1-p1-unscored",
        paper_id="p1",
        page_number=1,
        source="hybrid_page",
        score=None,
        validation_state="validated",
    )
    packet = EvidencePacket(
        packet_id="ep-unscored",
        query="Q?",
        paper_scope=["p1"],
        units=[unit],
        citations=[],
    )

    limits = ChatService._packet_quality_limits(packet)

    assert WEAK_EVIDENCE_LIMIT not in limits


def test_no_paper_conversation_mode_does_not_run_orchestrator_or_retrieval():
    async def run():
        gateway = RecordingGateway(generate_text="General answer.")
        hybrid = RecordingHybridRetrievalService(_hybrid_result())
        orchestrator = RecordingOrchestrator(_orchestrator_result())
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
            hybrid_retrieval=hybrid,
            research_orchestrator_factory=lambda **kwargs: orchestrator,
        )
        request = ChatRequest(
            question="What is a literature review?",
            paper_ids=None,
            retrieval_mode="hybrid",
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            enable_agentic_retrieval=True,
        )

        response = await service.answer(request)

        assert hybrid.calls == []
        assert orchestrator.requests == []
        assert response.agent_trace is None
        assert response.stats.retrieval_attempted is False

    asyncio.run(run())


def test_visual_retrieval_mode_keeps_single_pass_fallback():
    async def run():
        gateway = RecordingGateway(generate_text="Visual answer with paper-abc p.3.")
        visrag = TrackingVisRAG()
        orchestrator = RecordingOrchestrator(_orchestrator_result())
        service = ChatService(
            visrag=visrag,
            vector_store=FixedVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
            hybrid_retrieval=RecordingHybridRetrievalService(_hybrid_result()),
            research_orchestrator_factory=lambda **kwargs: orchestrator,
        )
        request = ChatRequest(
            question="What is X?",
            paper_ids=["paper-abc"],
            retrieval_mode="visual",
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            enable_agentic_retrieval=True,
        )

        response = await service.answer(request)

        assert orchestrator.requests == []
        assert visrag.queries == ["What is X?"]
        assert response.agent_trace is None
        assert response.evidence_packet is not None

    asyncio.run(run())


def test_chat_service_clamps_evidence_images_to_three():
    async def run():
        gateway = RecordingUserContentGateway(generate_text="General answer.")
        service = ChatService(
            visrag=TrackingVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=gateway,
            page_image_resolver=None,
        )
        request = ChatRequest(
            question="What can you answer generally?",
            paper_ids=None,
            base_url="http://fake/v1",
            api_key="k",
            model="m",
            enable_image_context=True,
            max_evidence_images=10,
        )

        await service.answer(request)

        assert gateway.user_content_calls[0]["max_evidence_images"] == 3

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


def test_verify_packet_citations_removes_scoped_citations_when_packet_has_no_accepted_pages():
    packet = EvidencePacket(
        packet_id="ep-empty",
        query="Q?",
        paper_scope=["p1"],
        units=[],
        citations=[],
        limits=["Scoped retrieval returned no evidence; no paper citations are available."],
    )

    verified, removed = ChatService._verify_citations_against_packet(
        "The missing result is shown at p1 p.2.",
        packet,
    )

    assert "p1 p.2" not in verified
    assert removed == ["p1 p.2"]


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
