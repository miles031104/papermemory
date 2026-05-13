import asyncio

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.schemas.chat import ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
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
    assert "paper_id=paper-1" in prompt
    assert "page=7" in prompt
    assert "image_ref=/papers/paper-1/pages/7/image" in prompt


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

    response = asyncio.run(service.answer(ChatRequest(question="What is shown?")))
    user_content = gateway.messages[-1]["content"]

    assert response.note == "Generation request included 1 retrieved page image(s)."
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
                enable_image_context=True,
                max_evidence_images=1,
            )
        )
    )
    user_content = gateway.messages[-1]["content"]

    assert response.note == "Generation request included 1 retrieved page image(s)."
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

    response = asyncio.run(service.answer(ChatRequest(question="What is shown?")))
    user_content = gateway.messages[-1]["content"]

    assert response.note == "Generation request used text-only evidence context."
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

    response = asyncio.run(service.answer(ChatRequest(question="What is shown?")))
    user_content = gateway.messages[-1]["content"]

    assert response.note == "Generation request included 1 retrieved page image(s)."
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert str(external_image) not in user_content[0]["text"]
    assert str(controlled_image) not in user_content[0]["text"]
