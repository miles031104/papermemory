from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any
from uuid import UUID, uuid5

from fastapi import HTTPException, status

from app.core.config import Settings
from app.schemas.retrieval import PageEvidence


POINT_ID_NAMESPACE = UUID("9bfa0a83-9d63-44b1-8b47-f3b58a7257fc")
PAYLOAD_RESERVED_KEYS = {"paper_id", "page_number", "image_path", "title", "caption"}


class VectorStoreUnavailable(HTTPException):
    """Raised when Qdrant cannot be used for an operational reason."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {detail}",
        )


@dataclass(frozen=True)
class _FallbackPointStruct:
    id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True)
class _FallbackVectorParams:
    size: int
    distance: str


@dataclass(frozen=True)
class _FallbackMatchValue:
    value: Any


@dataclass(frozen=True)
class _FallbackMatchAny:
    any: list[Any]


@dataclass(frozen=True)
class _FallbackFieldCondition:
    key: str
    match: Any


@dataclass(frozen=True)
class _FallbackFilter:
    must: list[Any]


class _FallbackModels:
    PointStruct = _FallbackPointStruct
    VectorParams = _FallbackVectorParams
    MatchValue = _FallbackMatchValue
    MatchAny = _FallbackMatchAny
    FieldCondition = _FallbackFieldCondition
    Filter = _FallbackFilter


class VectorStore:
    """Qdrant-backed storage for page-image embeddings and retrieval metadata."""

    def __init__(
        self,
        settings: Settings,
        client: Any | None = None,
        qdrant_models: Any | None = None,
    ) -> None:
        self.url = settings.qdrant_url
        self.collection = settings.qdrant_collection
        self.vector_size = settings.qdrant_vector_size
        self.distance = settings.qdrant_distance
        self.timeout = settings.qdrant_timeout_seconds
        self._collection_ready = False

        self.models = qdrant_models or self._load_qdrant_models_or_fallback()
        self.client = client or self._build_qdrant_client()

    async def upsert_page(
        self,
        paper_id: str,
        page_number: int,
        embedding: list[float],
        image_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._validate_embedding(embedding)
        await self._ensure_collection()

        payload = self._page_payload(
            paper_id=paper_id,
            page_number=page_number,
            image_path=image_path,
            metadata=metadata,
        )
        point = self.models.PointStruct(
            id=self.point_id(paper_id=paper_id, page_number=page_number),
            vector=embedding,
            payload=payload,
        )

        try:
            await self.client.upsert(
                collection_name=self.collection,
                points=[point],
                wait=True,
            )
        except Exception as exc:
            raise VectorStoreUnavailable(f"failed to upsert page {paper_id}/{page_number}: {exc}") from exc

    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
    ) -> list[PageEvidence]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        self._validate_embedding(embedding)
        await self._ensure_collection()

        query_filter = self._paper_filter(paper_ids)
        try:
            hits = await self._query_points(
                embedding=embedding,
                top_k=top_k,
                query_filter=query_filter,
            )
        except Exception as exc:
            raise VectorStoreUnavailable(f"failed to search pages: {exc}") from exc

        evidence = [self._hit_to_evidence(hit) for hit in hits]
        return sorted(evidence, key=lambda item: item.score, reverse=True)

    @staticmethod
    def point_id(paper_id: str, page_number: int) -> str:
        return str(uuid5(POINT_ID_NAMESPACE, f"{paper_id}:{page_number}"))

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return

        try:
            exists = await self.client.collection_exists(self.collection)
            if not exists:
                await self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=self.models.VectorParams(
                        size=self.vector_size,
                        distance=self._qdrant_distance(),
                    ),
                )
            elif hasattr(self.client, "get_collection"):
                await self._validate_existing_collection()
        except Exception as exc:
            if isinstance(exc, VectorStoreUnavailable):
                raise
            raise VectorStoreUnavailable(f"failed to ensure collection '{self.collection}': {exc}") from exc

        self._collection_ready = True

    async def _validate_existing_collection(self) -> None:
        info = await self.client.get_collection(self.collection)
        vectors = getattr(getattr(getattr(info, "config", None), "params", None), "vectors", None)
        if isinstance(vectors, dict):
            vectors = next(iter(vectors.values()), None)
        if vectors is None:
            return

        existing_size = getattr(vectors, "size", None)
        existing_distance = getattr(vectors, "distance", None)
        existing_distance_name = getattr(existing_distance, "value", existing_distance)

        if existing_size is not None and int(existing_size) != self.vector_size:
            raise VectorStoreUnavailable(
                f"collection '{self.collection}' has vector size {existing_size}, but PaperMemory is configured for "
                f"{self.vector_size}. Recreate the collection and reindex papers after changing retrieval mode."
            )
        if existing_distance_name and str(existing_distance_name).lower() != self.distance.lower():
            raise VectorStoreUnavailable(
                f"collection '{self.collection}' uses distance {existing_distance_name}, but PaperMemory is configured "
                f"for {self.distance}. Recreate the collection and reindex papers after changing retrieval mode."
            )

    async def _query_points(
        self,
        embedding: list[float],
        top_k: int,
        query_filter: Any | None,
    ) -> list[Any]:
        if hasattr(self.client, "query_points"):
            response = await self.client.query_points(
                collection_name=self.collection,
                query=embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
            return list(getattr(response, "points", response))

        return list(
            await self.client.search(
                collection_name=self.collection,
                query_vector=embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
        )

    def _build_qdrant_client(self) -> Any:
        try:
            client_module = import_module("qdrant_client")
            async_client = getattr(client_module, "AsyncQdrantClient")
        except (ImportError, AttributeError) as exc:
            raise VectorStoreUnavailable(
                "qdrant-client is not installed. Install the API dependencies before using retrieval."
            ) from exc

        return async_client(url=self.url, timeout=self.timeout)

    def _load_qdrant_models_or_fallback(self) -> Any:
        try:
            return import_module("qdrant_client.models")
        except ImportError:
            return _FallbackModels

    def _qdrant_distance(self) -> Any:
        distance_model = getattr(self.models, "Distance", None)
        if distance_model is None:
            return self.distance
        return getattr(distance_model, self.distance.upper())

    def _paper_filter(self, paper_ids: list[str] | None) -> Any | None:
        if not paper_ids:
            return None

        match = (
            self.models.MatchValue(value=paper_ids[0])
            if len(paper_ids) == 1
            else self.models.MatchAny(any=paper_ids)
        )
        return self.models.Filter(
            must=[
                self.models.FieldCondition(
                    key="paper_id",
                    match=match,
                )
            ]
        )

    def _page_payload(
        self,
        paper_id: str,
        page_number: int,
        image_path: str,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "paper_id": paper_id,
            "page_number": page_number,
            "image_path": image_path,
        }
        if metadata:
            payload.update({key: value for key, value in metadata.items() if value is not None})
        return payload

    def _hit_to_evidence(self, hit: Any) -> PageEvidence:
        payload = getattr(hit, "payload", None) or {}
        try:
            paper_id = str(payload["paper_id"])
            page_number = int(payload["page_number"])
            score = float(getattr(hit, "score"))
        except (KeyError, TypeError, ValueError) as exc:
            raise VectorStoreUnavailable(f"Qdrant result is missing required page payload: {payload}") from exc

        metadata = {
            key: str(value)
            for key, value in payload.items()
            if key not in PAYLOAD_RESERVED_KEYS and value is not None
        }

        return PageEvidence(
            paper_id=paper_id,
            page_number=page_number,
            score=score,
            image_path=self._optional_str(payload.get("image_path")),
            title=self._optional_str(payload.get("title")),
            caption=self._optional_str(payload.get("caption")),
            metadata=metadata or None,
        )

    def _validate_embedding(self, embedding: list[float]) -> None:
        if len(embedding) != self.vector_size:
            raise ValueError(
                f"Embedding has size {len(embedding)}, expected {self.vector_size} for collection '{self.collection}'."
            )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)
