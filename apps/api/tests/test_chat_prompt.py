import asyncio

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.schemas.chat import ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.context_builder import PAPERMEMORY_SYSTEM_PROMPT as BUILDER_SYSTEM_PROMPT
from app.services.context_builder import RECENT_CONVERSATION_MESSAGE_LIMIT
from app.services.context_builder import build_evisrag_prompt as build_context_prompt
from app.services.chat_service import ChatService, PAPERMEMORY_SYSTEM_PROMPT
from app.services.model_gateway import GenerationResponse, ModelGateway
from app.services.page_image_resolver import PageImageResolver


class FakeEmbedding:
    vector = [0.1, 0.2]


class FakeVisRAG:
    async def embed_query(self, query: str) -> FakeEmbedding:
        return FakeEmbedding()


class FakeVectorStore:
    def __init__(self, evidence: list[PageEvidence]) -> None:
        self.evidence = evidence

    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
    ) -> list[PageEvidence]:
        return self.evidence


class RecordingModelGateway(ModelGateway):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.messages = []

    async def generate(
        self,
        messages,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> GenerationResponse:
        self.messages = messages
        return GenerationResponse(text="answer", model=model or self.model)


def test_evisrag_prompt_mentions_page_evidence() -> None:
    service = ChatService(visrag=None, vector_store=None, model_gateway=None)  # type: ignore[arg-type]

    prompt = service.build_evisrag_prompt(
        question="What does the ablation table show?",
        evidence=[
            PageEvidence(
                paper_id="paper-1",
                page_number=7,
                score=0.91,
                image_path=".papermemory/rendered_pages/paper-1/page-0007.png",
                caption="Ablation results",
            )
        ],
    )

    assert "EVisRAG-style" in prompt
    assert "do not narrate the workflow" in prompt
    assert "**Answer**" in prompt
    assert "**Evidence**" in prompt
    assert "**Limits**" in prompt
    assert "hidden reasoning" in prompt
    assert "paper_id=paper-1" in prompt
    assert "page=7" in prompt
    assert "citation_id=paper-1 p.7" in prompt
    assert "image_ref=/papers/paper-1/pages/7/image" in prompt


def test_evisrag_prompt_does_not_trust_evidence_image_url() -> None:
    service = ChatService(visrag=None, vector_store=None, model_gateway=None)  # type: ignore[arg-type]
    local_image_url = r"C:\Users\Miles\secret.png"

    prompt = service.build_evisrag_prompt(
        question="What does the ablation table show?",
        evidence=[
            PageEvidence(
                paper_id="paper-1",
                page_number=7,
                score=0.91,
                image_url=local_image_url,
                caption="Ablation results",
            )
        ],
    )

    assert local_image_url not in prompt
    assert "image_ref=/papers/paper-1/pages/7/image" in prompt


def test_empty_evidence_prompt_uses_conversation_mode() -> None:
    service = ChatService(visrag=None, vector_store=None, model_gateway=None)  # type: ignore[arg-type]

    prompt = service.build_evisrag_prompt(
        question="Can we talk about research planning?",
        evidence=[],
    )

    assert "conversation mode" in prompt
    assert "No retrieved paper evidence is available" in prompt
    assert "Do not include paper citations" in prompt


def test_scoped_retrieval_without_evidence_is_not_labeled_conversation_mode() -> None:
    service = ChatService(visrag=None, vector_store=None, model_gateway=None)  # type: ignore[arg-type]

    prompt = service.build_evisrag_prompt(
        question="What does this paper claim?",
        evidence=[],
        retrieval_attempted=True,
    )

    assert "scoped retrieval mode" in prompt
    assert "Scoped retrieval returned no evidence" in prompt
    assert "conversation mode" not in prompt
    assert "Do not include paper citations" in prompt


def test_system_prompt_hides_reasoning_without_blocking_internal_reasoning() -> None:
    assert PAPERMEMORY_SYSTEM_PROMPT == BUILDER_SYSTEM_PROMPT
    assert "Reason internally" in PAPERMEMORY_SYSTEM_PROMPT
    assert "never expose hidden reasoning" in PAPERMEMORY_SYSTEM_PROMPT
    assert "Do not narrate the retrieval process" in PAPERMEMORY_SYSTEM_PROMPT
    assert "general research conversation" in PAPERMEMORY_SYSTEM_PROMPT


def test_chat_service_delegates_prompt_building_to_context_builder() -> None:
    service = ChatService(visrag=None, vector_store=None, model_gateway=None)  # type: ignore[arg-type]
    evidence = [
        PageEvidence(
            paper_id="paper-1",
            page_number=7,
            score=0.91,
            image_path=".papermemory/rendered_pages/paper-1/page-0007.png",
            caption="Ablation results",
        )
    ]

    assert service.build_evisrag_prompt(
        question="What does the ablation table show?",
        evidence=evidence,
        retrieval_attempted=True,
    ) == build_context_prompt(
        question="What does the ablation table show?",
        evidence=evidence,
        retrieval_attempted=True,
    )


def test_chat_service_caps_prior_messages_before_generation() -> None:
    settings = Settings()
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(evidence=[]),  # type: ignore[arg-type]
        model_gateway=gateway,
    )
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"history-{index}"}
        for index in range(RECENT_CONVERSATION_MESSAGE_LIMIT + 3)
    ]
    request = ChatRequest(question="Can we discuss research plans?", messages=history)
    original_messages = [message.model_dump() for message in request.messages]

    response = asyncio.run(service.answer(request))

    assert [message.model_dump() for message in request.messages] == original_messages
    assert gateway.messages[0] == {"role": "system", "content": PAPERMEMORY_SYSTEM_PROMPT}
    assert gateway.messages[1:-1] == original_messages[-RECENT_CONVERSATION_MESSAGE_LIMIT:]
    assert len(gateway.messages) == RECENT_CONVERSATION_MESSAGE_LIMIT + 2
    assert gateway.messages[-1]["role"] == "user"
    assert gateway.messages[-1]["content"] == response.prompt_preview
    assert "conversation mode" in gateway.messages[-1]["content"]


def test_chat_service_preserves_short_prior_message_history() -> None:
    settings = Settings()
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(
            evidence=[
                PageEvidence(
                    paper_id="paper-1",
                    page_number=3,
                    score=0.82,
                    caption="Method overview",
                )
            ]
        ),  # type: ignore[arg-type]
        model_gateway=gateway,
    )
    history = [
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
    ]
    request = ChatRequest(question="What is the method?", paper_ids=["paper-1"], messages=history)
    original_messages = [message.model_dump() for message in request.messages]

    response = asyncio.run(service.answer(request))

    assert gateway.messages[1:-1] == original_messages
    assert [message.model_dump() for message in request.messages] == original_messages
    assert gateway.messages[-1]["role"] == "user"
    assert gateway.messages[-1]["content"] == response.prompt_preview
    assert "Use an EVisRAG-style evidence-first workflow" in gateway.messages[-1]["content"]
    assert "citation_id=paper-1 p.3" in gateway.messages[-1]["content"]


def test_chat_service_preserves_empty_prior_message_history() -> None:
    settings = Settings()
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(evidence=[]),  # type: ignore[arg-type]
        model_gateway=gateway,
    )

    response = asyncio.run(service.answer(ChatRequest(question="Can we discuss research plans?")))

    assert len(gateway.messages) == 2
    assert gateway.messages[0] == {"role": "system", "content": PAPERMEMORY_SYSTEM_PROMPT}
    assert gateway.messages[-1]["role"] == "user"
    assert gateway.messages[-1]["content"] == response.prompt_preview
    assert "conversation mode" in gateway.messages[-1]["content"]


def test_chat_service_adds_page_image_content_when_enabled(tmp_path) -> None:
    image_path = tmp_path / "rendered_pages" / "paper-1" / "page-0001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    settings = Settings(storage_root=tmp_path, byok_enable_image_context=True)
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(
            evidence=[
                PageEvidence(
                    paper_id="paper-1",
                    page_number=1,
                    score=0.9,
                    image_path=str(image_path),
                )
            ]
        ),  # type: ignore[arg-type]
        model_gateway=gateway,
        page_image_resolver=PageImageResolver(StoragePaths(settings)),
    )

    response = asyncio.run(service.answer(ChatRequest(question="What is shown?", paper_ids=["paper-1"])))
    user_content = gateway.messages[-1]["content"]

    assert response.status == "success"
    assert response.note == "Generation request included 1 retrieved page image(s)."
    assert response.stats.retrieval_attempted is True
    assert response.stats.paper_scope_count == 1
    assert response.stats.evidence_count == 1
    assert response.stats.included_image_count == 1
    assert response.limits == []
    assert user_content[0]["type"] == "text"
    assert str(image_path) not in user_content[0]["text"]
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_chat_request_can_enable_image_context_for_one_request(tmp_path) -> None:
    image_path = tmp_path / "rendered_pages" / "paper-1" / "page-0001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    settings = Settings(storage_root=tmp_path, byok_enable_image_context=False)
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(
            evidence=[
                PageEvidence(
                    paper_id="paper-1",
                    page_number=1,
                    score=0.9,
                    image_path=str(image_path),
                )
            ]
        ),  # type: ignore[arg-type]
        model_gateway=gateway,
        page_image_resolver=PageImageResolver(StoragePaths(settings)),
    )

    response = asyncio.run(
        service.answer(
            ChatRequest(
                question="What is shown?",
                paper_ids=["paper-1"],
                enable_image_context=True,
                max_evidence_images=1,
            )
        )
    )
    user_content = gateway.messages[-1]["content"]

    assert response.status == "success"
    assert response.note == "Generation request included 1 retrieved page image(s)."
    assert response.stats.included_image_count == 1
    assert response.limits == []
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_chat_service_ignores_malicious_payload_image_path(tmp_path) -> None:
    external_image = tmp_path / "external.png"
    external_image.write_bytes(b"\x89PNG\r\n\x1a\nsecret")
    settings = Settings(storage_root=tmp_path / "storage", byok_enable_image_context=True)
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(
            evidence=[
                PageEvidence(
                    paper_id="paper-1",
                    page_number=1,
                    score=0.9,
                    image_path=str(external_image),
                )
            ]
        ),  # type: ignore[arg-type]
        model_gateway=gateway,
        page_image_resolver=PageImageResolver(StoragePaths(settings)),
    )

    response = asyncio.run(service.answer(ChatRequest(question="What is shown?", paper_ids=["paper-1"])))
    user_content = gateway.messages[-1]["content"]

    assert response.status == "success"
    assert response.note == "Generation request used text-only evidence context."
    assert response.stats.retrieval_attempted is True
    assert response.stats.paper_scope_count == 1
    assert response.stats.evidence_count == 1
    assert response.stats.included_image_count == 0
    assert response.limits == ["Text-only evidence context; no page images were included."]
    assert user_content == service.build_evisrag_prompt(
        question="What is shown?",
        evidence=service.vector_store.evidence,  # type: ignore[attr-defined]
    )
    assert str(external_image) not in user_content


def test_chat_service_uses_controlled_page_image_despite_malicious_payload_path(tmp_path) -> None:
    external_image = tmp_path / "external.png"
    external_image.write_bytes(b"\x89PNG\r\n\x1a\nsecret")
    controlled_image = tmp_path / "storage" / "rendered_pages" / "paper-1" / "page-0001.png"
    controlled_image.parent.mkdir(parents=True)
    controlled_image.write_bytes(b"\x89PNG\r\n\x1a\nsafe")
    settings = Settings(storage_root=tmp_path / "storage", byok_enable_image_context=True)
    gateway = RecordingModelGateway(settings)
    service = ChatService(
        visrag=FakeVisRAG(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(
            evidence=[
                PageEvidence(
                    paper_id="paper-1",
                    page_number=1,
                    score=0.9,
                    image_path=str(external_image),
                )
            ]
        ),  # type: ignore[arg-type]
        model_gateway=gateway,
        page_image_resolver=PageImageResolver(StoragePaths(settings)),
    )

    response = asyncio.run(service.answer(ChatRequest(question="What is shown?", paper_ids=["paper-1"])))
    user_content = gateway.messages[-1]["content"]

    assert response.status == "success"
    assert response.note == "Generation request included 1 retrieved page image(s)."
    assert response.stats.included_image_count == 1
    assert response.limits == []
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert str(external_image) not in user_content[0]["text"]
    assert str(controlled_image) not in user_content[0]["text"]
