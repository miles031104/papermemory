from pathlib import Path
from typing import Sequence

from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService


class IndexingService:
    """Indexes rendered PDF page images into the page vector store."""

    def __init__(self, visrag: VisRAGService, vector_store: VectorStore) -> None:
        self.visrag = visrag
        self.vector_store = vector_store

    async def index_pages(self, paper_id: str, page_paths: Sequence[Path]) -> None:
        for page_number, page_path in enumerate(page_paths, start=1):
            embedding = await self.visrag.embed_page_image(str(page_path))
            await self.vector_store.upsert_page(
                paper_id=paper_id,
                page_number=page_number,
                embedding=embedding.vector,
                image_path=str(page_path),
                metadata={
                    "embedding_model": embedding.model,
                    "embedding_instruction": embedding.instruction,
                },
            )
