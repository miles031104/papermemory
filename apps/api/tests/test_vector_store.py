import asyncio
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.services.vector_store import VectorStore


class FakeQdrantClient:
    def __init__(self, *, exists: bool = True, hits: list[Any] | None = None) -> None:
        self.exists = exists
        self.hits = hits or []
        self.created_collection: dict[str, Any] | None = None
        self.upserts: list[dict[str, Any]] = []
        self.queries: list[dict[str, Any]] = []

    async def collection_exists(self, collection_name: str) -> bool:
        self.queries.append({"method": "collection_exists", "collection_name": collection_name})
        return self.exists

    async def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.created_collection = {
            "collection_name": collection_name,
            "vectors_config": vectors_config,
        }
        self.exists = True

    async def upsert(self, collection_name: str, points: list[Any], wait: bool) -> None:
        self.upserts.append(
            {
                "collection_name": collection_name,
                "points": points,
                "wait": wait,
            }
        )

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        query_filter: Any | None,
        limit: int,
        with_payload: bool,
        with_vectors: bool,
    ) -> Any:
        self.queries.append(
            {
                "method": "query_points",
                "collection_name": collection_name,
                "query": query,
                "query_filter": query_filter,
                "limit": limit,
                "with_payload": with_payload,
                "with_vectors": with_vectors,
            }
        )
        return QueryResponse(points=self.hits)


@dataclass
class QueryResponse:
    points: list[Any]


@dataclass
class Hit:
    score: float
    payload: dict[str, Any]


def test_upsert_page_creates_collection_and_payload() -> None:
    client = FakeQdrantClient(exists=False)
    settings = Settings(qdrant_collection="test_pages", qdrant_vector_size=3)
    store = VectorStore(settings=settings, client=client)

    asyncio.run(
        store.upsert_page(
            paper_id="paper-1",
            page_number=7,
            embedding=[0.1, 0.2, 0.3],
            image_path=".papermemory/papers/paper-1/pages/page-0007.png",
            metadata={"title": "Attention", "caption": "Ablation table", "local_note": "kept"},
        )
    )

    assert client.created_collection is not None
    assert client.created_collection["collection_name"] == "test_pages"
    assert client.created_collection["vectors_config"].size == 3
    assert client.upserts[0]["collection_name"] == "test_pages"
    assert client.upserts[0]["wait"] is True

    point = client.upserts[0]["points"][0]
    assert point.id == VectorStore.point_id(paper_id="paper-1", page_number=7)
    assert point.vector == [0.1, 0.2, 0.3]
    assert point.payload == {
        "paper_id": "paper-1",
        "page_number": 7,
        "image_path": ".papermemory/papers/paper-1/pages/page-0007.png",
        "title": "Attention",
        "caption": "Ablation table",
        "local_note": "kept",
    }


def test_search_pages_filters_and_maps_evidence_sorted_by_score() -> None:
    client = FakeQdrantClient(
        exists=True,
        hits=[
            Hit(
                score=0.2,
                payload={
                    "paper_id": "paper-1",
                    "page_number": 2,
                    "image_path": "low.png",
                },
            ),
            Hit(
                score=0.9,
                payload={
                    "paper_id": "paper-1",
                    "page_number": 1,
                    "image_path": "high.png",
                    "title": "VisRAG",
                    "caption": "Method overview",
                    "local_tag": "important",
                    "embedding_model": "openbmb/VisRAG-Ret",
                    "source_path": r"C:\Users\Miles CUI\private\source.pdf",
                },
            ),
        ],
    )
    settings = Settings(qdrant_collection="test_pages", qdrant_vector_size=3)
    store = VectorStore(settings=settings, client=client)

    evidence = asyncio.run(
        store.search_pages(
            embedding=[0.3, 0.2, 0.1],
            top_k=2,
            paper_ids=["paper-1"],
        )
    )

    query_call = client.queries[-1]
    assert query_call["method"] == "query_points"
    assert query_call["collection_name"] == "test_pages"
    assert query_call["limit"] == 2
    assert query_call["with_payload"] is True
    assert query_call["with_vectors"] is False
    assert query_call["query_filter"].must[0].key == "paper_id"
    assert query_call["query_filter"].must[0].match.value == "paper-1"

    assert [item.score for item in evidence] == [0.9, 0.2]
    assert evidence[0].paper_id == "paper-1"
    assert evidence[0].page_number == 1
    assert evidence[0].image_path == "high.png"
    assert evidence[0].image_url == "/papers/paper-1/pages/1/image"
    assert evidence[0].title == "VisRAG"
    assert evidence[0].caption == "Method overview"
    assert evidence[0].metadata == {"embedding_model": "openbmb/VisRAG-Ret"}


def test_search_pages_empty_paper_scope_returns_empty_without_querying_qdrant() -> None:
    client = FakeQdrantClient(
        exists=True,
        hits=[
            Hit(
                score=0.9,
                payload={"paper_id": "paper-1", "page_number": 1, "image_path": "high.png"},
            )
        ],
    )
    settings = Settings(qdrant_collection="test_pages", qdrant_vector_size=3)
    store = VectorStore(settings=settings, client=client)

    evidence = asyncio.run(
        store.search_pages(
            embedding=[0.3, 0.2, 0.1],
            top_k=2,
            paper_ids=[],
        )
    )

    assert evidence == []
    assert client.queries == []
