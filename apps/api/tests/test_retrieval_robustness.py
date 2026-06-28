import asyncio

from app.schemas.chat import ChatRequest
from app.schemas.evidence import EvidencePacket
from app.services.chat_service import (
    CONVERSATION_MODE_LIMIT,
    NO_SCOPED_EVIDENCE_LIMIT,
    ChatService,
)
from app.services.hybrid_retrieval_service import HybridRetrievalResult
from app.services.research_orchestrator import OrchestratorRequest, ResearchOrchestrator
from eval.robustness.fixtures import (
    EmptyVectorStore,
    RecordingGateway,
    RecordingHybridRetrieval,
    RecordingPlanner,
    StaticOrchestratorFactory,
    StubVisRAG,
    make_hybrid_result,
    make_orchestrator_result,
    make_packet,
    make_unit,
)


def _service(
    answer_text: str,
    *,
    hybrid_result: HybridRetrievalResult | None = None,
    orchestrator_packet: EvidencePacket | None = None,
) -> ChatService:
    orchestrator_factory = None
    if orchestrator_packet is not None:
        orchestrator_factory = StaticOrchestratorFactory(
            make_orchestrator_result(orchestrator_packet)
        )

    return ChatService(
        visrag=StubVisRAG(),
        vector_store=EmptyVectorStore(),
        model_gateway=RecordingGateway(answer_text),
        hybrid_retrieval=RecordingHybridRetrieval(
            hybrid_result or make_hybrid_result([], limits=[NO_SCOPED_EVIDENCE_LIMIT])
        ),
        research_orchestrator_factory=orchestrator_factory,
    )


def test_empty_scope_strips_paper_citations_and_marks_conversation_mode_limit() -> None:
    async def run():
        service = _service("Unsupported claim with paper-ghost p.9.")
        response = await service.answer(
            ChatRequest(
                question="What does my selected paper say?",
                paper_ids=None,
                retrieval_mode="hybrid",
                model="stub",
                base_url="http://fake.local/v1",
                api_key="key",
            )
        )

        assert response.stats.retrieval_attempted is False
        assert response.evidence_packet is not None
        assert response.evidence_packet.units == []
        assert "paper-ghost p.9" not in response.answer
        assert CONVERSATION_MODE_LIMIT in response.limits

    asyncio.run(run())


def test_missing_scoped_evidence_is_partial_limited_and_cites_nothing() -> None:
    async def run():
        service = _service(
            "The scoped answer is at paper-1 p.4.",
            hybrid_result=make_hybrid_result([], paper_id="paper-1", limits=[NO_SCOPED_EVIDENCE_LIMIT]),
        )
        response = await service.answer(
            ChatRequest(
                question="What does paper-1 say?",
                paper_ids=["paper-1"],
                retrieval_mode="hybrid",
                enable_agentic_retrieval=False,
                model="stub",
                base_url="http://fake.local/v1",
                api_key="key",
            )
        )

        assert response.status == "partial"
        assert response.evidence_packet is not None
        assert response.evidence_packet.units == []
        assert response.evidence_packet.citations == []
        assert "paper-1 p.4" not in response.answer
        assert NO_SCOPED_EVIDENCE_LIMIT in response.limits

    asyncio.run(run())


def test_no_new_evidence_second_pass_stops_with_trace_reason() -> None:
    async def run():
        retrieval = RecordingHybridRetrieval(
            make_hybrid_result([1]),
            make_hybrid_result([1], query="same accepted page"),
        )
        planner = RecordingPlanner(
            {
                "next_queries": ["same accepted page"],
                "retrieval_mode": "hybrid",
                "missing_evidence": ["independent page"],
            }
        )
        request = OrchestratorRequest(
            question="What supports the claim?",
            paper_ids=["paper-1"],
            top_k=5,
            score_threshold=None,
            max_per_paper=None,
            messages=[],
            model="stub",
            base_url="http://fake.local/v1",
            api_key="key",
        )

        result = await ResearchOrchestrator(retrieval=retrieval, planner=planner).run(request)

        assert [call["query"] for call in retrieval.calls] == [
            "What supports the claim?",
            "same accepted page",
        ]
        assert result.agent_trace.final_stop_reason == "no_new_evidence"
        assert any(
            action.state == "sufficiency_check"
            and action.stop_reason == "no_new_evidence"
            for action in result.agent_trace.actions
        )

    asyncio.run(run())


def test_citation_drift_outside_accepted_packet_is_stripped() -> None:
    async def run():
        packet = make_packet([make_unit(2)], paper_scope=["paper-1"])
        service = _service(
            "Supported by paper-1 p.2, not paper-1 p.99.",
            orchestrator_packet=packet,
        )
        response = await service.answer(
            ChatRequest(
                question="Where is the result?",
                paper_ids=["paper-1"],
                retrieval_mode="hybrid",
                enable_agentic_retrieval=True,
                model="stub",
                base_url="http://fake.local/v1",
                api_key="key",
            )
        )

        assert "paper-1 p.2" in response.answer
        assert "paper-1 p.99" not in response.answer

    asyncio.run(run())


def test_citation_drift_unknown_paper_id_is_stripped() -> None:
    async def run():
        packet = make_packet([make_unit(2)], paper_scope=["paper-1"])
        service = _service(
            "Supported by paper-1 p.2, not paper-evil p.9.",
            orchestrator_packet=packet,
        )
        response = await service.answer(
            ChatRequest(
                question="Where is the result?",
                paper_ids=["paper-1"],
                retrieval_mode="hybrid",
                enable_agentic_retrieval=True,
                model="stub",
                base_url="http://fake.local/v1",
                api_key="key",
            )
        )

        assert "paper-1 p.2" in response.answer
        assert "paper-evil p.9" not in response.answer

    asyncio.run(run())


def test_conflicting_evidence_adds_uncertainty_limit() -> None:
    async def run():
        packet = make_packet(
            [
                make_unit(4, caption="The reported accuracy is 91% on the benchmark."),
                make_unit(7, caption="The reported accuracy is 74% on the benchmark."),
            ],
            paper_scope=["paper-1"],
        )
        service = _service(
            "The accuracy is 91% with paper-1 p.4 and paper-1 p.7.",
            orchestrator_packet=packet,
        )
        response = await service.answer(
            ChatRequest(
                question="What accuracy should I report?",
                paper_ids=["paper-1"],
                retrieval_mode="hybrid",
                enable_agentic_retrieval=True,
                model="stub",
                base_url="http://fake.local/v1",
                api_key="key",
            )
        )

        assert any("conflicting" in limit.lower() for limit in response.limits)
        assert "verify" in " ".join(response.limits).lower()
        assert "conflicting" in response.prompt_preview.lower()

    asyncio.run(run())


def test_low_text_or_scanned_marker_adds_visual_first_limit() -> None:
    async def run():
        packet = make_packet(
            [
                make_unit(
                    6,
                    caption="Fig. 2",
                    metadata={"text_quality": "empty", "ocr_needed": "true"},
                )
            ],
            paper_scope=["paper-1"],
        )
        service = _service(
            "The diagram says the method works at paper-1 p.6.",
            orchestrator_packet=packet,
        )
        response = await service.answer(
            ChatRequest(
                question="What does the scanned page say?",
                paper_ids=["paper-1"],
                retrieval_mode="hybrid",
                enable_agentic_retrieval=True,
                model="stub",
                base_url="http://fake.local/v1",
                api_key="key",
            )
        )

        limit_text = " ".join(response.limits).lower()
        assert "low-text" in limit_text or "ocr" in limit_text
        assert "visual-first" in limit_text
        assert "visual-first" in response.prompt_preview.lower()

    asyncio.run(run())
