import asyncio
from pathlib import Path
from typing import Any

from app.services.indexing_service import IndexingService
from app.services.visrag_service import EmbeddingResult


class FakeVisRAG:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def embed_page_image(self, image_path: str) -> EmbeddingResult:
        self.calls.append(image_path)
        return EmbeddingResult(
            vector=[0.6, 0.8],
            model="openbmb/VisRAG-Ret",
            instruction="Represent this query for retrieving relevant documents:",
        )


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts: list[dict[str, Any]] = []

    async def upsert_page(
        self,
        paper_id: str,
        page_number: int,
        embedding: list[float],
        image_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.upserts.append(
            {
                "paper_id": paper_id,
                "page_number": page_number,
                "embedding": embedding,
                "image_path": image_path,
                "metadata": metadata,
            }
        )


def test_index_pages_uses_visrag_image_embeddings_and_writes_metadata(
    tmp_path: Path,
) -> None:
    page_paths = [tmp_path / "page-0001.png", tmp_path / "page-0002.png"]
    for page_path in page_paths:
        page_path.write_bytes(b"rendered page")

    visrag = FakeVisRAG()
    vector_store = FakeVectorStore()
    service = IndexingService(visrag=visrag, vector_store=vector_store)  # type: ignore[arg-type]

    asyncio.run(service.index_pages("paper-1", page_paths))

    assert visrag.calls == [str(path) for path in page_paths]
    assert vector_store.upserts == [
        {
            "paper_id": "paper-1",
            "page_number": 1,
            "embedding": [0.6, 0.8],
            "image_path": str(page_paths[0]),
            "metadata": {
                "embedding_model": "openbmb/VisRAG-Ret",
                "embedding_instruction": (
                    "Represent this query for retrieving relevant documents:"
                ),
            },
        },
        {
            "paper_id": "paper-1",
            "page_number": 2,
            "embedding": [0.6, 0.8],
            "image_path": str(page_paths[1]),
            "metadata": {
                "embedding_model": "openbmb/VisRAG-Ret",
                "embedding_instruction": (
                    "Represent this query for retrieving relevant documents:"
                ),
            },
        },
    ]
