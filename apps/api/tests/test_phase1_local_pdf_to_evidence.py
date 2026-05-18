import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.schemas.papers import PaperMetadata, PaperStatus
from app.services.indexing_service import IndexingService
from app.services.ingestion_service import IngestionService
from app.services.pdf_renderer import PdfRenderer
from app.services.vector_store import VectorStore
from app.services.visrag_service import EmbeddingResult


class ConstantVisRAG:
    """Deterministic no-model embedding source for end-to-end local smoke tests."""

    def __init__(self, vector_size: int) -> None:
        self.model_name = "phase1a-stub-visrag"
        self.instruction = "Phase 1A deterministic local smoke"
        self.vector = [1.0] + [0.0] * (vector_size - 1)

    async def embed_page_image(self, image_path: str) -> EmbeddingResult:
        assert Path(image_path).is_file()
        return EmbeddingResult(
            vector=self.vector,
            model=self.model_name,
            instruction=self.instruction,
        )

    async def embed_query(self, query: str) -> EmbeddingResult:
        assert query
        return EmbeddingResult(
            vector=self.vector,
            model=self.model_name,
            instruction=self.instruction,
        )


def _minimal_pdf_bytes() -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page(width=300, height=180)
    page.insert_text((36, 72), "PaperMemory Phase 1A PDF evidence smoke", fontsize=12)
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


def test_local_pdf_render_index_and_retrieve_evidence_smoke(tmp_path: Path) -> None:
    async def run_smoke() -> None:
        settings = Settings(
            storage_root=tmp_path / "storage",
            qdrant_mode="local",
            qdrant_local_path=tmp_path / "qdrant-local",
            qdrant_collection="phase1a_pdf_evidence_smoke",
            qdrant_vector_size=8,
            visrag_backend="stub",
            max_pdf_pages=5,
            pdf_render_zoom=1.0,
        )
        visrag = ConstantVisRAG(vector_size=settings.qdrant_vector_size)
        vector_store = VectorStore(settings=settings)
        service = IngestionService(
            paths=StoragePaths(settings),
            renderer=PdfRenderer(
                zoom=settings.pdf_render_zoom,
                max_pages=settings.max_pdf_pages,
            ),
            indexing_service=IndexingService(
                visrag=visrag,  # type: ignore[arg-type]
                vector_store=vector_store,
            ),
            max_upload_bytes=settings.max_upload_bytes,
        )

        try:
            upload = UploadFile(
                filename="phase1a.pdf",
                file=BytesIO(_minimal_pdf_bytes()),
            )
            paper = await service.accept_pdf_upload(file=upload, title="Phase 1A Smoke")

            assert paper.status == PaperStatus.ready
            assert paper.page_count == 1

            metadata_path = settings.storage_root / "papers" / paper.paper_id / "metadata.json"
            metadata = PaperMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
            assert metadata.status == PaperStatus.ready
            assert metadata.page_count == 1

            page_image_path = (
                settings.storage_root
                / "rendered_pages"
                / paper.paper_id
                / "page-0001.png"
            )
            assert page_image_path.is_file()
            assert page_image_path.stat().st_size > 8
            assert page_image_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
            assert settings.qdrant_local_path.is_dir()

            query_embedding = await visrag.embed_query("find the Phase 1A smoke page")
            evidence = await vector_store.search_pages(
                embedding=query_embedding.vector,
                top_k=3,
                paper_ids=[paper.paper_id],
            )

            assert len(evidence) >= 1
            first = evidence[0]
            assert first.paper_id == paper.paper_id
            assert first.page_number == 1
            assert first.score > 0.99
            assert first.image_path == str(page_image_path)
            assert first.image_url == f"/papers/{paper.paper_id}/pages/1/image"
            assert first.metadata == {
                "embedding_model": "phase1a-stub-visrag",
                "embedding_instruction": "Phase 1A deterministic local smoke",
            }
        finally:
            await _close_qdrant_client(vector_store)

    asyncio.run(run_smoke())
