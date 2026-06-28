import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from app.schemas.agent_trace import AgentTrace, AgentTraceAction
from app.schemas.evidence import EvidenceCitation, EvidencePacket, EvidenceUnit
from app.schemas.chat import ChatRequest
from app.schemas.reliability import CoverageStatus, EvidenceCoverageReport
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.hybrid_retrieval_service import HybridRetrievalResult
from app.services.model_gateway import BuiltUserContent, GenerationResponse, ModelGateway
from app.services.research_orchestrator import OrchestratorResult


class RecordingGateway(ModelGateway):
    def __init__(self, text: str, tokens: list[str] | None = None) -> None:
        self.text = text
        self.tokens = tokens or [text]

    async def generate(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> GenerationResponse:
        return GenerationResponse(text=self.text, model="stub")

    async def generate_stream(
        self,
        messages: Any,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        for token in self.tokens:
            yield token

    def build_user_content(self, text: str, image_paths, **kwargs) -> BuiltUserContent:
        return BuiltUserContent(content=text, included_image_count=0)


class EmptyVectorStore:
    async def search_pages(self, **kwargs):
        return []


class StubVisRAG:
    async def embed_query(self, query: str):
        return type("Embedding", (), {"vector": [1.0], "model": "stub", "instruction": "stub"})()


class RecordingRequirementService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def plan(self, *, question: str, paper_ids: list[str] | None):
        from app.schemas.reliability import EvidenceRequirement, QuestionIntent

        self.calls.append({"question": question, "paper_ids": paper_ids})
        return EvidenceRequirement(
            requirement_id="er-chat",
            intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
            required_claim_types=["number", "recommendation"],
            must_verify_numeric_claims=True,
        )


class RecordingOrchestrator:
    def __init__(self, result: OrchestratorResult) -> None:
        self.result = result
        self.requests: list[Any] = []

    async def run(self, request) -> OrchestratorResult:
        self.requests.append(request)
        return self.result


class RecordingHybridRetrieval:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def search(self, **kwargs) -> HybridRetrievalResult:
        self.calls.append(kwargs)
        return self.result


class FailingRequirementService:
    def plan(self, **kwargs):
        raise AssertionError("requirement planner should not run when reliability is disabled")


class FailingCoverageService:
    def evaluate(self, **kwargs):
        raise AssertionError("coverage evaluator should not run when reliability is disabled")


class FailingAnswerVerifier:
    def verify(self, **kwargs):
        raise AssertionError("answer verifier should not run when reliability is disabled")


def _orchestrator_result(coverage_status: CoverageStatus = CoverageStatus.strong) -> OrchestratorResult:
    evidence = [
        PageEvidence(
            paper_id="paper-1",
            page_number=2,
            score=0.84,
            caption="The accepted evidence reports 80% success.",
        )
    ]
    unit = EvidenceUnit(
        evidence_id="ev-paper-1-p2",
        paper_id="paper-1",
        page_number=2,
        source="hybrid_page",
        score=0.84,
        title="Runtime policy evaluation",
        caption="The accepted evidence reports 80% success.",
        metadata={"recommendation": "runtime policy enforcement"},
        validation_state="validated",
    )
    packet = EvidencePacket(
        packet_id="ep-reliability-chat",
        query="What should we claim?",
        paper_scope=["paper-1"],
        units=[unit],
        citations=[
            EvidenceCitation(
                evidence_id=unit.evidence_id,
                paper_id="paper-1",
                page_number=2,
                label="paper-1 p.2",
            )
        ],
    )
    trace = AgentTrace(
        trace_id="trace-reliability",
        actions=[
            AgentTraceAction(
                state="coverage_check",
                pass_index=1,
                evidence_ids=[unit.evidence_id],
                note="coverage status: strong",
            ),
            AgentTraceAction(
                state="answer",
                pass_index=1,
                evidence_ids=[unit.evidence_id],
                stop_reason="sufficient",
            ),
        ],
        final_stop_reason="sufficient",
    )
    coverage = EvidenceCoverageReport(
        requirement_id="er-chat",
        status=coverage_status,
        covered_paper_ids=["paper-1"],
        covered_claim_types=["number", "recommendation"],
        matched_numbers=["80%"],
    )
    return OrchestratorResult(
        evidence=evidence,
        evidence_packet=packet,
        agent_trace=trace,
        limits=[],
        coverage_report=coverage,
    )


def _hybrid_result() -> HybridRetrievalResult:
    orchestrator_result = _orchestrator_result()
    return HybridRetrievalResult(
        status="success",
        evidence=orchestrator_result.evidence,
        evidence_packet=orchestrator_result.evidence_packet,
        limits=[],
    )


def _service(answer_text: str, orchestrator: RecordingOrchestrator, requirement_service):
    return ChatService(
        visrag=StubVisRAG(),
        vector_store=EmptyVectorStore(),
        model_gateway=RecordingGateway(answer_text, tokens=[answer_text]),
        hybrid_retrieval=object(),
        research_orchestrator_factory=lambda **kwargs: orchestrator,
        evidence_requirement_service=requirement_service,
    )


def test_answer_includes_reliability_report_when_enabled() -> None:
    async def run():
        requirement_service = RecordingRequirementService()
        orchestrator = RecordingOrchestrator(_orchestrator_result())
        service = _service(
            "The accepted evidence reports 80% success and recommends runtime policy enforcement.",
            orchestrator,
            requirement_service,
        )

        response = await service.answer(
            ChatRequest(
                question="What numbers should we report?",
                paper_ids=["paper-1"],
                base_url="http://fake.local/v1",
                api_key="key",
                model="test-model",
            )
        )

        assert response.reliability_report is not None
        assert response.reliability_report.status == "strong"
        assert response.reliability_report.requirement.intent.intent_type == "numeric_grounding"
        assert orchestrator.requests[0].evidence_requirement is response.reliability_report.requirement

    asyncio.run(run())


def test_disabled_reliability_layer_does_not_plan_or_attach_report() -> None:
    async def run():
        requirement_service = RecordingRequirementService()
        hybrid = RecordingHybridRetrieval(_hybrid_result())
        service = ChatService(
            visrag=StubVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=RecordingGateway("The accepted evidence reports 80% success."),
            hybrid_retrieval=hybrid,
            research_orchestrator_factory=lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("orchestrator should not run when reliability is disabled")
            ),
            evidence_requirement_service=requirement_service,
        )

        response = await service.answer(
            ChatRequest(
                question="What numbers should we report?",
                paper_ids=["paper-1"],
                base_url="http://fake.local/v1",
                api_key="key",
                model="test-model",
                enable_reliability_layer=False,
            )
        )

        assert requirement_service.calls == []
        assert len(hybrid.calls) == 1
        assert response.reliability_report is None

    asyncio.run(run())


def test_disabled_reliability_layer_uses_non_orchestrated_hybrid_path() -> None:
    async def run():
        hybrid = RecordingHybridRetrieval(_hybrid_result())

        def fail_if_orchestrator_is_built(**kwargs):
            raise AssertionError("orchestrator planner path should not run when reliability is disabled")

        service = ChatService(
            visrag=StubVisRAG(),
            vector_store=EmptyVectorStore(),
            model_gateway=RecordingGateway("The accepted evidence reports 80% success."),
            hybrid_retrieval=hybrid,
            research_orchestrator_factory=fail_if_orchestrator_is_built,
            evidence_requirement_service=FailingRequirementService(),
            evidence_coverage_service=FailingCoverageService(),
            answer_claim_verifier=FailingAnswerVerifier(),
        )

        response = await service.answer(
            ChatRequest(
                question="What numbers should we report?",
                paper_ids=["paper-1"],
                base_url="http://fake.local/v1",
                api_key="key",
                model="test-model",
                enable_reliability_layer=False,
                enable_agentic_retrieval=True,
                retrieval_mode="hybrid",
            )
        )

        assert len(hybrid.calls) == 1
        assert hybrid.calls[0]["query"] == "What numbers should we report?"
        assert response.agent_trace is None
        assert response.reliability_report is None

    asyncio.run(run())


def test_streaming_final_dict_includes_report_but_early_evidence_frame_does_not() -> None:
    async def run():
        orchestrator = RecordingOrchestrator(_orchestrator_result())
        service = _service(
            "The accepted evidence reports 80% success and recommends runtime policy enforcement.",
            orchestrator,
            RecordingRequirementService(),
        )

        chunks = []
        async for chunk in service.answer_stream(
            ChatRequest(
                question="What numbers should we report?",
                paper_ids=["paper-1"],
                base_url="http://fake.local/v1",
                api_key="key",
                model="test-model",
            )
        ):
            chunks.append(chunk)

        assert "reliability_report" not in chunks[0]
        assert chunks[-1]["reliability_report"] is not None
        assert chunks[-1]["reliability_report"].status == "strong"

    asyncio.run(run())


def test_unsupported_answer_claim_merges_reliability_limit() -> None:
    async def run():
        orchestrator = RecordingOrchestrator(_orchestrator_result())
        service = _service(
            "The accepted evidence reports 94% success and recommends runtime policy enforcement.",
            orchestrator,
            RecordingRequirementService(),
        )

        response = await service.answer(
            ChatRequest(
                question="What numbers should we report?",
                paper_ids=["paper-1"],
                base_url="http://fake.local/v1",
                api_key="key",
                model="test-model",
            )
        )

        assert response.reliability_report is not None
        assert response.reliability_report.status == "partial"
        assert response.reliability_report.unsupported_claim_count == 1
        assert "One or more answer claims are not supported by accepted evidence." in response.limits

    asyncio.run(run())
