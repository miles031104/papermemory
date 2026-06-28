import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.main import create_app
from app.routers import retrieval
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService, LOW_TEXT_EVIDENCE_LIMIT
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.page_text_extractor import (
    PageTextEntry,
    PageTextQuality,
    TextBlock,
    TextManifest,
)
from app.services.text_manifest_store import TextManifestStore


def _quality(
    text: str | None,
    *,
    has_text: bool = True,
    quality_label: str | None = None,
) -> PageTextQuality:
    words = text.split() if text else []
    label = quality_label or ("good" if has_text and text else "empty")
    return PageTextQuality(
        char_count=len(text or ""),
        word_count=len(words),
        block_count=1 if text else 0,
        has_text=has_text,
        ocr_needed=not has_text or label == "low_text",
        quality_label=label,
    )


def _page(
    paper_id: str,
    page_number: int,
    text: str | None,
    *,
    quality_label: str | None = None,
) -> PageTextEntry:
    return PageTextEntry(
        paper_id=paper_id,
        page_number=page_number,
        width=612.0,
        height=792.0,
        text=text,
        caption=text[:120] if text else None,
        blocks=[
            TextBlock(
                block_number=0,
                text=text,
                bbox=(0.0, 0.0, 612.0, 792.0),
                word_count=len(text.split()),
            )
        ]
        if text
        else [],
        words=[],
        quality=_quality(text, quality_label=quality_label),
    )


def _manifest(paper_id: str, pages: list[PageTextEntry]) -> TextManifest:
    return TextManifest(paper_id=paper_id, page_count=len(pages), pages=pages)


class _FakeEmbedding:
    vector = [1.0, 0.0]


class _FakeVisRAG:
    model_name = "fake-visrag"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def embed_query(self, query: str) -> _FakeEmbedding:
        self.queries.append(query)
        return _FakeEmbedding()


class _FakeVectorStore:
    def __init__(self, evidence: list[PageEvidence]) -> None:
        self.evidence = evidence
        self.calls: list[dict[str, object]] = []

    async def search_pages(
        self,
        embedding: list[float],
        top_k: int,
        paper_ids: list[str] | None = None,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> list[PageEvidence]:
        self.calls.append(
            {
                "embedding": embedding,
                "top_k": top_k,
                "paper_ids": paper_ids,
                "score_threshold": score_threshold,
                "max_per_paper": max_per_paper,
            }
        )
        return self.evidence[:top_k]


class _FakeManifestStore:
    def __init__(self, manifests: dict[str, TextManifest]) -> None:
        self.manifests = manifests
        self.loads: list[str] = []

    def load(self, paper_id: str) -> TextManifest:
        self.loads.append(paper_id)
        if paper_id not in self.manifests:
            raise FileNotFoundError(paper_id)
        return self.manifests[paper_id]


def _run(coro):
    return asyncio.run(coro)


def test_hybrid_overlap_dedupes_page_and_preserves_both_rank_traces() -> None:
    visual = PageEvidence(
        paper_id="paper-a",
        page_number=1,
        score=0.91,
        caption="visual caption should lose when BM25 text exists",
    )
    manifest = _manifest(
        "paper-a",
        [_page("paper-a", 1, "The BM25 overlap page explains reciprocal rank fusion.")],
    )
    service = HybridRetrievalService(
        visrag=_FakeVisRAG(),
        vector_store=_FakeVectorStore([visual]),
        manifest_store=_FakeManifestStore({"paper-a": manifest}),
    )

    result = _run(
        service.search(query="BM25 reciprocal fusion", paper_ids=["paper-a"], top_k=5)
    )

    assert result.status == "success"
    assert [(item.paper_id, item.page_number) for item in result.evidence] == [("paper-a", 1)]
    assert result.evidence[0].score == pytest.approx((1 / 61) + (1 / 61))
    assert "BM25 overlap page" in (result.evidence[0].caption or "")
    unit = result.evidence_packet.units[0]
    assert unit.source == "hybrid_page"
    assert unit.validation_state == "validated"
    assert unit.score == pytest.approx(result.evidence[0].score)
    assert [(trace.retriever, trace.source, trace.rank) for trace in unit.rank_trace] == [
        ("visrag", "visrag_page", 1),
        ("bm25", "text_page", 1),
    ]
    assert unit.rank_trace[0].score == pytest.approx(0.91)
    assert unit.rank_trace[1].score is not None


def test_hybrid_returns_visual_only_and_text_only_pages() -> None:
    visual_only = PageEvidence(
        paper_id="paper-a",
        page_number=2,
        score=0.84,
        caption="layout figure visual page",
    )
    manifest = _manifest(
        "paper-a",
        [
            _page("paper-a", 1, "Lexical BM25 terms live on a text-only page."),
            _page("paper-a", 3, "Unrelated appendix."),
        ],
    )
    service = HybridRetrievalService(
        visrag=_FakeVisRAG(),
        vector_store=_FakeVectorStore([visual_only]),
        manifest_store=_FakeManifestStore({"paper-a": manifest}),
    )

    result = _run(service.search(query="Lexical BM25 terms", paper_ids=["paper-a"], top_k=5))

    pages = {(item.paper_id, item.page_number) for item in result.evidence}
    assert pages == {("paper-a", 1), ("paper-a", 2)}
    units = {(unit.paper_id, unit.page_number): unit for unit in result.evidence_packet.units}
    assert [trace.retriever for trace in units[("paper-a", 1)].rank_trace] == ["bm25"]
    assert [trace.retriever for trace in units[("paper-a", 2)].rank_trace] == ["visrag"]


def test_low_text_quality_metadata_flows_through_hybrid_evidence() -> None:
    manifest = _manifest(
        "paper-a",
        [_page("paper-a", 1, "BM25", quality_label="low_text")],
    )
    service = HybridRetrievalService(
        visrag=_FakeVisRAG(),
        vector_store=_FakeVectorStore([]),
        manifest_store=_FakeManifestStore({"paper-a": manifest}),
    )

    result = _run(service.search(query="BM25", paper_ids=["paper-a"], top_k=5))

    evidence_metadata = result.evidence[0].metadata or {}
    assert evidence_metadata["quality_label"] == "low_text"
    assert evidence_metadata["ocr_needed"] == "true"

    unit_metadata = result.evidence_packet.units[0].metadata or {}
    assert unit_metadata["quality_label"] == "low_text"
    assert unit_metadata["ocr_needed"] == "true"
    assert unit_metadata["char_count"] == "4"
    assert unit_metadata["word_count"] == "1"
    assert LOW_TEXT_EVIDENCE_LIMIT in ChatService._packet_quality_limits(
        result.evidence_packet
    )


def test_empty_paper_scope_returns_validated_empty_packet_without_searching() -> None:
    vector_store = _FakeVectorStore(
        [PageEvidence(paper_id="paper-a", page_number=1, score=0.9)]
    )
    manifest_store = _FakeManifestStore(
        {"paper-a": _manifest("paper-a", [_page("paper-a", 1, "BM25 text")])}
    )
    service = HybridRetrievalService(
        visrag=_FakeVisRAG(),
        vector_store=vector_store,
        manifest_store=manifest_store,
    )

    result = _run(service.search(query="BM25", paper_ids=[], top_k=5))

    assert result.status == "partial"
    assert result.evidence == []
    assert result.evidence_packet.units == []
    assert result.evidence_packet.citations == []
    assert vector_store.calls == []
    assert manifest_store.loads == []
    assert result.limits == ["No paper scope selected; retrieval skipped."]


def test_missing_text_manifest_keeps_visual_hits_and_records_limit() -> None:
    visual = PageEvidence(paper_id="paper-a", page_number=1, score=0.77)
    service = HybridRetrievalService(
        visrag=_FakeVisRAG(),
        vector_store=_FakeVectorStore([visual]),
        manifest_store=_FakeManifestStore({}),
    )

    result = _run(service.search(query="anything", paper_ids=["paper-a"], top_k=5))

    assert [(item.paper_id, item.page_number) for item in result.evidence] == [("paper-a", 1)]
    assert result.limits == ["Text manifest missing for one or more scoped papers."]
    assert [trace.retriever for trace in result.evidence_packet.units[0].rank_trace] == ["visrag"]


def test_text_manifest_loading_is_limited_to_selected_papers_and_max_per_paper_applies_after_fusion() -> None:
    manifest_a = _manifest(
        "paper-a",
        [
            _page("paper-a", 1, "BM25 shared keyword primary page."),
            _page("paper-a", 2, "BM25 shared keyword secondary page."),
        ],
    )
    manifest_b = _manifest("paper-b", [_page("paper-b", 1, "BM25 shared keyword beta.")])
    manifest_out = _manifest(
        "paper-out",
        [_page("paper-out", 1, "BM25 shared keyword must not leak.")],
    )
    manifest_store = _FakeManifestStore(
        {"paper-a": manifest_a, "paper-b": manifest_b, "paper-out": manifest_out}
    )
    service = HybridRetrievalService(
        visrag=_FakeVisRAG(),
        vector_store=_FakeVectorStore([]),
        manifest_store=manifest_store,
    )

    result = _run(
        service.search(
            query="BM25 shared keyword",
            paper_ids=["paper-a", "paper-b"],
            top_k=5,
            max_per_paper=1,
        )
    )

    assert manifest_store.loads == ["paper-a", "paper-b"]
    assert {item.paper_id for item in result.evidence} == {"paper-a", "paper-b"}
    assert len([item for item in result.evidence if item.paper_id == "paper-a"]) == 1
    assert ("paper-out", 1) not in {
        (item.paper_id, item.page_number) for item in result.evidence
    }


def test_default_route_stays_visual_and_hybrid_route_returns_validated_packet(
    tmp_path: Path,
) -> None:
    settings = Settings(storage_root=tmp_path / "storage")
    paths = StoragePaths(settings)
    paths.ensure_all()
    paths.paper_dir("paper-a").mkdir(parents=True, exist_ok=True)
    paths.paper_metadata_path("paper-a").write_text("{}", encoding="utf-8")
    paths.page_images_dir("paper-a").mkdir(parents=True, exist_ok=True)
    paths.page_image_path("paper-a", 1).write_bytes(b"png")
    TextManifestStore(paths).save(
        _manifest(
            "paper-a",
            [_page("paper-a", 1, "BM25 route overlap proves hybrid mode uses text.")],
        )
    )
    vector_store = _FakeVectorStore(
        [PageEvidence(paper_id="paper-a", page_number=1, score=0.9, caption="visual route")]
    )
    api = create_app()
    api.dependency_overrides[retrieval.get_settings] = lambda: settings
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: _FakeVisRAG()
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store
    client = TestClient(api)

    visual_response = client.post(
        "/retrieval/search",
        json={"query": "BM25 route overlap", "paper_ids": ["paper-a"]},
    )
    hybrid_response = client.post(
        "/retrieval/search",
        json={
            "query": "BM25 route overlap",
            "paper_ids": ["paper-a"],
            "retrieval_mode": "hybrid",
        },
    )

    assert visual_response.status_code == 200
    assert visual_response.json()["retrieval_model"] == "fake-visrag"
    assert visual_response.json()["evidence_packet"]["units"][0]["source"] == "visrag_page"
    assert hybrid_response.status_code == 200
    hybrid_body = hybrid_response.json()
    assert hybrid_body["retrieval_model"] == "fake-visrag+bm25"
    assert hybrid_body["evidence_packet"]["units"][0]["source"] == "hybrid_page"
    assert [trace["retriever"] for trace in hybrid_body["evidence_packet"]["units"][0]["rank_trace"]] == [
        "visrag",
        "bm25",
    ]
