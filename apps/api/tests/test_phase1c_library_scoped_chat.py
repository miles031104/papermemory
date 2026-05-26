import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.main import create_app
from app.routers import chat, papers
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.indexing_service import IndexingService
from app.services.ingestion_service import IngestionService
from app.services.model_gateway import GenerationResponse, ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.pdf_renderer import PdfRenderer
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService


class RecordingModelGateway(ModelGateway):
    """Fake BYOK gateway that records chat-completion inputs without network I/O."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        messages,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> GenerationResponse:
        content = messages[-1]["content"]
        user_text = content[0]["text"] if isinstance(content, list) else content
        answer = (
            "Phase 1C fake gateway conversation answer without paper grounding."
            if "conversation mode" in user_text
            else "Phase 1C fake gateway answer grounded in scoped page evidence."
        )
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "base_url": base_url,
                "api_key": api_key,
                "temperature": temperature,
            }
        )
        return GenerationResponse(
            text=answer,
            model="phase1c-fake-response-model",
        )


class ExplodingVisRAG:
    model_name = "should-not-be-used"

    async def embed_query(self, query: str):
        raise AssertionError("empty paper scope should not embed the query")


class ExplodingVectorStore:
    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        raise AssertionError("empty paper scope should not search the vector store")


def _minimal_pdf_bytes(label: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page(width=320, height=180)
    page.insert_text((36, 72), label, fontsize=12)
    payload = document.tobytes()
    document.close()
    assert payload.startswith(b"%PDF")
    return payload


async def _close_qdrant_client(store: VectorStore) -> None:
    close = getattr(store.client, "close", None)
    if close is None:
        return
    result = close()
    if hasattr(result, "__await__"):
        await result


def _upload_ready_pdf(client: TestClient, *, filename: str, title: str, label: str) -> dict[str, Any]:
    response = client.post(
        "/papers/upload",
        data={"title": title},
        files={"file": (filename, _minimal_pdf_bytes(label), "application/pdf")},
    )
    assert response.status_code == 201
    paper = response.json()["paper"]
    assert paper["status"] == "ready"
    assert paper["page_count"] == 1
    return paper


def _create_library_with_papers(client: TestClient, name: str, paper_ids: list[str]) -> dict[str, Any]:
    response = client.post(
        "/workspace/libraries",
        json={"name": name, "description": "Phase 1C scoped chat library"},
    )
    assert response.status_code == 201

    library_id = response.json()["id"]
    updated = client.patch(
        f"/workspace/libraries/{library_id}",
        json={"paper_ids": paper_ids},
    )
    assert updated.status_code == 200
    assert updated.json()["paper_ids"] == paper_ids
    return updated.json()


def _last_user_text(content: Any) -> str:
    if isinstance(content, list):
        text_part = content[0]
        assert text_part["type"] == "text"
        return text_part["text"]
    assert isinstance(content, str)
    return content


def test_uploaded_library_scope_can_chat_through_fake_byok_gateway(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        qdrant_mode="local",
        qdrant_local_path=tmp_path / "qdrant-local",
        qdrant_collection="phase1c_library_scoped_chat",
        qdrant_vector_size=8,
        visrag_backend="stub",
        max_pdf_pages=5,
        pdf_render_zoom=1.0,
        byok_enable_image_context=False,
    )
    paths = StoragePaths(settings)
    visrag = VisRAGService(settings=settings)
    vector_store = VectorStore(settings=settings)
    gateway = RecordingModelGateway(settings)
    ingestion_service = IngestionService(
        paths=paths,
        renderer=PdfRenderer(
            zoom=settings.pdf_render_zoom,
            max_pages=settings.max_pdf_pages,
        ),
        indexing_service=IndexingService(
            visrag=visrag,
            vector_store=vector_store,
        ),
        max_upload_bytes=settings.max_upload_bytes,
    )

    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[papers.get_ingestion_service] = lambda: ingestion_service
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=visrag,
        vector_store=vector_store,
        model_gateway=gateway,
        page_image_resolver=PageImageResolver(paths),
    )

    try:
        with TestClient(api) as client:
            paper_a = _upload_ready_pdf(
                client,
                filename="phase1c-a.pdf",
                title="Phase 1C Paper A",
                label="Phase 1C scoped chat evidence for paper A",
            )
            paper_b = _upload_ready_pdf(
                client,
                filename="phase1c-b.pdf",
                title="Phase 1C Paper B",
                label="Phase 1C out-of-scope evidence for paper B",
            )
            library_a = _create_library_with_papers(client, "Phase 1C Active Library", [paper_a["paper_id"]])
            _create_library_with_papers(client, "Phase 1C Other Library", [paper_b["paper_id"]])

            response = client.post(
                "/chat",
                json={
                    "question": "What does the Phase 1C scoped paper say?",
                    "paper_ids": library_a["paper_ids"],
                    "top_k": 5,
                    "model": "phase1c-request-model",
                    "base_url": "https://models.example.test/v1",
                    "api_key": "phase1c-secret-key",
                    "temperature": 0.35,
                    "enable_image_context": True,
                    "max_evidence_images": 1,
                },
            )

            assert response.status_code == 200
            body = response.json()
            body_text = json.dumps(body)

            assert body["answer"] == "Phase 1C fake gateway answer grounded in scoped page evidence."
            assert body["status"] == "success"
            assert body["model"] == "phase1c-fake-response-model"
            assert body["note"] == "Generation request included 1 retrieved page image(s)."
            assert body["stats"] == {
                "retrieval_attempted": True,
                "paper_scope_count": 1,
                "evidence_count": 1,
                "included_image_count": 1,
            }
            assert body["limits"] == []
            assert {item["paper_id"] for item in body["evidence"]} == {paper_a["paper_id"]}
            assert paper_b["paper_id"] not in body_text
            assert "rendered_pages" not in body_text
            assert str(tmp_path) not in body_text

            assert len(gateway.calls) == 2
            planner_call = gateway.calls[0]
            assert "retrieval planner" in planner_call["messages"][0]["content"]

            recorded = gateway.calls[1]
            assert recorded["model"] == "phase1c-request-model"
            assert recorded["base_url"] == "https://models.example.test/v1"
            assert recorded["api_key"] == "phase1c-secret-key"
            assert recorded["temperature"] == 0.35

            last_message = recorded["messages"][-1]
            assert last_message["role"] == "user"
            user_content = last_message["content"]
            user_text = _last_user_text(user_content)
            expected_image_ref = f"/papers/{paper_a['paper_id']}/pages/1/image"

            assert "Use an EVisRAG-style evidence-first workflow" in user_text
            assert f"paper_id={paper_a['paper_id']}" in user_text
            assert f"image_ref={expected_image_ref}" in user_text
            assert paper_b["paper_id"] not in user_text
            assert str(tmp_path) not in json.dumps(user_content)
            assert "rendered_pages" not in json.dumps(user_content)
            assert user_content[1]["type"] == "image_url"
            assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    finally:
        asyncio.run(_close_qdrant_client(vector_store))


def test_chat_empty_paper_scope_uses_conversation_mode_without_retrieval() -> None:
    settings = Settings()
    gateway = RecordingModelGateway(settings)
    api = create_app()
    api.dependency_overrides[chat.get_chat_service] = lambda: ChatService(
        visrag=ExplodingVisRAG(),  # type: ignore[arg-type]
        vector_store=ExplodingVectorStore(),  # type: ignore[arg-type]
        model_gateway=gateway,
    )

    with TestClient(api) as client:
        response = client.post(
            "/chat",
            json={
                "question": "Should an empty active library call the model?",
                "paper_ids": [],
                "model": "phase1c-request-model",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["evidence"] == []
    assert body["model"] == "phase1c-fake-response-model"
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
    assert body["answer"] == "Phase 1C fake gateway conversation answer without paper grounding."
    assert "conversation mode" in body["prompt_preview"]
    assert len(gateway.calls) == 1
