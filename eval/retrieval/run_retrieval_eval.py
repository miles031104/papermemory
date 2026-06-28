from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.routers import retrieval  # noqa: E402
from app.schemas.retrieval import PageEvidence  # noqa: E402
from app.services.hybrid_retrieval_service import HybridRetrievalService  # noqa: E402
from app.services.page_text_extractor import (  # noqa: E402
    PageTextEntry,
    PageTextQuality,
    TextBlock,
    TextManifest,
)
from app.services.text_retriever import TextRetriever  # noqa: E402
from app.services.vector_store import VectorStore  # noqa: E402


FIXTURE_PATH = REPO_ROOT / "eval" / "retrieval" / "golden_questions.jsonl"
RESULTS_DIR = REPO_ROOT / "eval" / "retrieval" / "results"
REPORT_METRICS_PATH = REPO_ROOT / "reports" / "final" / "results" / "baseline_metrics.md"
BM25_REPORT_METRICS_PATH = REPO_ROOT / "reports" / "final" / "results" / "bm25_metrics.md"
HYBRID_REPORT_METRICS_PATH = REPO_ROOT / "reports" / "final" / "results" / "hybrid_metrics.md"
KEYWORD_REPORT_METRICS_PATH = REPO_ROOT / "reports" / "final" / "results" / "keyword_baseline_metrics.md"

REQUIRED_FIXTURE_FIELDS = {
    "question",
    "paper_ids",
    "expected_pages",
    "answer_key",
    "must_cite_pages",
    "should_refuse",
    "question_type",
}
REQUIRED_SCOPE_FIELDS = {"library_id", "group_id", "provenance"}
SYNTHETIC_BOUNDARY = (
    "Synthetic smoke corpus over the current /retrieval/search API; "
    "not a real-PDF, real-VisRAG, or real-local-corpus benchmark."
)
BM25_SYNTHETIC_BOUNDARY = (
    "Synthetic BM25-only baseline over Node 3 TextManifest objects; "
    "not a real-PDF, real-corpus, hybrid, RRF, or VisRAG benchmark."
)
HYBRID_SYNTHETIC_BOUNDARY = (
    "Synthetic fixture baseline for page-canonical hybrid BM25 plus VisRAG RRF; "
    "not a real-PDF, real-corpus, or real-corpus improvement benchmark."
)
KEYWORD_SYNTHETIC_BOUNDARY = (
    "Deterministic keyword overlap baseline over synthetic page titles and captions; "
    "not an LLM, BM25, VisRAG, real-PDF, or real-corpus benchmark."
)

FEATURE_GROUPS = (
    ("visrag", {"visrag", "visual", "image", "images", "page-image", "page", "pages", "rendered"}),
    ("layout", {"layout", "layouts", "figure", "figures", "table", "tables", "diagram", "diagrams"}),
    ("bm25", {"bm25", "lexical", "exact", "term", "terms", "matching", "baseline"}),
    ("manifest", {"pymupdf", "manifest", "text", "extraction", "deterministic"}),
    ("ocr", {"ocr", "scanned", "weak-text", "quality", "flag", "needed"}),
    ("planner", {"bounded", "query", "planner", "rewrite", "rewriting", "agentic"}),
    ("refusal", {"zero-result", "retry", "refusal", "refuse", "missing", "evidence"}),
    ("citation", {"citation", "citations", "cite", "cites", "correctness", "page-level", "expected"}),
    ("privacy", {"local", "local-first", "privacy", "private", "commercial", "value"}),
    ("packet", {"packet", "packets", "verification", "verified", "provenance"}),
    ("hybrid", {"hybrid", "rrf", "fusion", "fuse", "rank"}),
    ("evaluation", {"golden", "evaluation", "eval", "metric", "metrics", "negative"}),
)

TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")


@dataclass(frozen=True)
class SyntheticPage:
    paper_id: str
    page_number: int
    title: str
    caption: str
    group_id: str


@dataclass(frozen=True)
class SyntheticEmbedding:
    vector: list[float]


@dataclass(frozen=True)
class SyntheticPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True)
class SyntheticScoredPoint:
    score: float
    payload: dict[str, Any]


@dataclass(frozen=True)
class SyntheticQueryResponse:
    points: list[SyntheticScoredPoint]


class SyntheticQdrantClient:
    """Small Qdrant-compatible in-memory client used only by Node 1 eval."""

    def __init__(self) -> None:
        self.points: list[SyntheticPoint] = []
        self.collection_ready = False

    async def collection_exists(self, collection_name: str) -> bool:
        return self.collection_ready

    async def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.collection_ready = True

    async def upsert(self, collection_name: str, points: list[Any], wait: bool = True) -> None:
        next_points = [
            SyntheticPoint(
                id=str(point.id),
                vector=[float(value) for value in point.vector],
                payload=dict(point.payload),
            )
            for point in points
        ]
        existing_ids = {point.id for point in next_points}
        self.points = [point for point in self.points if point.id not in existing_ids]
        self.points.extend(next_points)

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        query_filter: Any | None,
        limit: int,
        with_payload: bool = True,
        with_vectors: bool = False,
        score_threshold: float | None = None,
    ) -> SyntheticQueryResponse:
        allowed_papers = self._allowed_paper_ids(query_filter)
        scored: list[SyntheticScoredPoint] = []
        for point in self.points:
            paper_id = str(point.payload.get("paper_id", ""))
            if allowed_papers is not None and paper_id not in allowed_papers:
                continue
            score = cosine_similarity(query, point.vector)
            if score_threshold is not None and score < score_threshold:
                continue
            scored.append(SyntheticScoredPoint(score=score, payload=dict(point.payload)))

        scored.sort(
            key=lambda point: (
                -point.score,
                str(point.payload.get("paper_id", "")),
                int(point.payload.get("page_number", 0)),
            )
        )
        return SyntheticQueryResponse(points=scored[:limit])

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        query_filter: Any | None,
        limit: int,
        with_payload: bool = True,
        with_vectors: bool = False,
        score_threshold: float | None = None,
    ) -> list[SyntheticScoredPoint]:
        response = await self.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            score_threshold=score_threshold,
        )
        return response.points

    def _allowed_paper_ids(self, query_filter: Any | None) -> set[str] | None:
        if query_filter is None:
            return None

        for condition in getattr(query_filter, "must", []) or []:
            if getattr(condition, "key", None) != "paper_id":
                continue
            match = getattr(condition, "match", None)
            match_any = getattr(match, "any", None)
            if match_any is not None:
                return {str(item) for item in match_any}
            match_value = getattr(match, "value", None)
            if match_value is not None:
                return {str(match_value)}
        return None


class SyntheticVisRAG:
    model_name = "synthetic-visrag-vectorizer"

    async def embed_query(self, query: str) -> SyntheticEmbedding:
        return SyntheticEmbedding(vector=vectorize_text(query))


class SyntheticTextManifestStore:
    def __init__(self, manifests: list[TextManifest]) -> None:
        self.manifests = {manifest.paper_id: manifest for manifest in manifests}

    def load(self, paper_id: str) -> TextManifest:
        manifest = self.manifests.get(paper_id)
        if manifest is None:
            raise FileNotFoundError(paper_id)
        return manifest


def synthetic_pages() -> list[SyntheticPage]:
    return [
        SyntheticPage(
            paper_id="demo-visrag-core",
            page_number=1,
            title="VisRAG Page-Image Retrieval",
            caption=(
                "VisRAG page-image retrieval embeds rendered PDF pages and page images "
                "for visual evidence search in PaperMemory."
            ),
            group_id="group-visual-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-visrag-core",
            page_number=2,
            title="Layout And Figure Grounding",
            caption=(
                "Visual retrieval preserves layout, figure, table, and diagram cues that "
                "may be lost in text-only extraction."
            ),
            group_id="group-visual-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-visrag-core",
            page_number=3,
            title="Hybrid Fusion Bridge",
            caption=(
                "Hybrid RRF fusion can combine visual page retrieval with future text "
                "ranks while keeping page provenance."
            ),
            group_id="group-visual-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-bm25-text",
            page_number=1,
            title="Planned BM25 Exact-Term Text Baseline",
            caption=(
                "A future BM25 lexical baseline is planned to test exact-term retrieval "
                "for method names, datasets, variables, abbreviations, and citation tokens."
            ),
            group_id="group-text-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-bm25-text",
            page_number=2,
            title="Planned PyMuPDF Text Manifest",
            caption=(
                "A future PyMuPDF manifest stage is planned to create deterministic "
                "per-page text and quality metadata for later BM25 indexing."
            ),
            group_id="group-text-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-bm25-text",
            page_number=3,
            title="OCR Needed Flag",
            caption=(
                "Scanned or weak-text pages should be flagged as OCR needed and kept "
                "visual-first until OCR is implemented."
            ),
            group_id="group-text-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-agentic-rag",
            page_number=1,
            title="Bounded Query Planner",
            caption=(
                "The bounded agentic query planner rewrites retrieval queries while "
                "preserving the selected paper scope."
            ),
            group_id="group-agentic-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-agentic-rag",
            page_number=2,
            title="Zero-Result Retry And Refusal",
            caption=(
                "Zero-result retry handles missing evidence by attempting one fallback "
                "retrieval before a refusal."
            ),
            group_id="group-agentic-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-agentic-rag",
            page_number=3,
            title="Evidence Delta Gate",
            caption=(
                "Follow-up retrieval must add new evidence; otherwise the bounded agent "
                "moves to sufficiency or refusal."
            ),
            group_id="group-agentic-retrieval",
        ),
        SyntheticPage(
            paper_id="demo-risk-eval",
            page_number=1,
            title="Negative Case Design",
            caption=(
                "Golden evaluation includes negative questions and refusal cases so the "
                "baseline does not measure only happy paths."
            ),
            group_id="group-evaluation-risk",
        ),
        SyntheticPage(
            paper_id="demo-risk-eval",
            page_number=2,
            title="Page Citation Correctness",
            caption=(
                "Page-level citation correctness checks whether cited evidence pages "
                "match the expected paper pages."
            ),
            group_id="group-evaluation-risk",
        ),
        SyntheticPage(
            paper_id="demo-risk-eval",
            page_number=3,
            title="Future EvidencePacket Commercial Value",
            caption=(
                "A future EvidencePacket citation-verification layer is planned to pair "
                "local-first privacy with checked page evidence as the commercial value proposition."
            ),
            group_id="group-evaluation-risk",
        ),
    ]


def build_synthetic_text_manifests() -> list[TextManifest]:
    pages_by_paper: dict[str, list[PageTextEntry]] = {}
    for page in synthetic_pages():
        text = f"{page.title}. {page.caption}"
        pages_by_paper.setdefault(page.paper_id, []).append(
            PageTextEntry(
                paper_id=page.paper_id,
                page_number=page.page_number,
                width=612.0,
                height=792.0,
                text=text,
                caption=page.caption,
                blocks=[
                    TextBlock(
                        block_number=0,
                        text=page.title,
                        bbox=(0.0, 0.0, 612.0, 72.0),
                        word_count=len(page.title.split()),
                    ),
                    TextBlock(
                        block_number=1,
                        text=page.caption,
                        bbox=(0.0, 72.0, 612.0, 792.0),
                        word_count=len(page.caption.split()),
                    ),
                ],
                words=[],
                quality=PageTextQuality(
                    char_count=len(text),
                    word_count=len(text.split()),
                    block_count=2,
                    has_text=True,
                    ocr_needed=False,
                    quality_label="good",
                ),
            )
        )

    return [
        TextManifest(
            paper_id=paper_id,
            page_count=len(pages),
            pages=sorted(pages, key=lambda item: item.page_number),
        )
        for paper_id, pages in sorted(pages_by_paper.items())
    ]


def vectorize_text(text: str) -> list[float]:
    tokens = TOKEN_RE.findall(text.lower())
    vector = []
    for _, aliases in FEATURE_GROUPS:
        vector.append(float(sum(1 for token in tokens if token in aliases)))
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


async def build_synthetic_vector_store() -> VectorStore:
    settings = Settings(
        qdrant_mode="local",
        qdrant_collection="papermemory_node1_synthetic_pages",
        qdrant_local_path=REPO_ROOT / "eval" / "retrieval" / ".synthetic_qdrant",
        qdrant_vector_size=len(FEATURE_GROUPS),
    )
    vector_store = VectorStore(settings=settings, client=SyntheticQdrantClient())
    for page in synthetic_pages():
        await vector_store.upsert_page(
            paper_id=page.paper_id,
            page_number=page.page_number,
            embedding=vectorize_text(f"{page.title} {page.caption}"),
            image_path=str(
                REPO_ROOT
                / "storage"
                / "rendered_pages"
                / page.paper_id
                / f"page-{page.page_number:04d}.png"
            ),
            caption=page.caption,
            metadata={
                "embedding_model": SyntheticVisRAG.model_name,
                "embedding_instruction": "Synthetic Node 1 vectorizer over page captions.",
                "group_id": page.group_id,
                "synthetic": "true",
            },
        )
    return vector_store


def build_synthetic_client() -> TestClient:
    vector_store = asyncio.run(build_synthetic_vector_store())
    visrag = SyntheticVisRAG()
    api = create_app()
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: visrag
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store
    return TestClient(api)


def load_fixture(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            missing = sorted(REQUIRED_FIXTURE_FIELDS.difference(row))
            if missing:
                raise ValueError(f"{path}:{line_number} missing required fields: {', '.join(missing)}")
            missing_scope = sorted(REQUIRED_SCOPE_FIELDS.difference(row))
            if missing_scope:
                raise ValueError(f"{path}:{line_number} missing scope/provenance fields: {', '.join(missing_scope)}")
            if not isinstance(row["paper_ids"], list):
                raise ValueError(f"{path}:{line_number} paper_ids must be a list")
            if not isinstance(row["expected_pages"], list):
                raise ValueError(f"{path}:{line_number} expected_pages must be a list")
            if not isinstance(row["must_cite_pages"], list):
                raise ValueError(f"{path}:{line_number} must_cite_pages must be a list")
            if not isinstance(row["should_refuse"], bool):
                raise ValueError(f"{path}:{line_number} should_refuse must be a boolean")
            if not isinstance(row["provenance"], dict):
                raise ValueError(f"{path}:{line_number} provenance must be an object")
            rows.append(row)
    return rows


def page_key(page: dict[str, Any]) -> tuple[str, int]:
    return str(page["paper_id"]), int(page["page_number"])


def format_page_key(key: tuple[str, int]) -> str:
    return f"{key[0]}:{key[1]}"


def evaluate_rows(client: TestClient, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        request = {
            "query": row["question"],
            "paper_ids": row["paper_ids"],
            "top_k": 5,
        }
        response = client.post("/retrieval/search", json=request)
        body = response.json()
        if response.status_code != 200:
            raise RuntimeError(
                f"retrieval failed for {row.get('id', row['question'])}: "
                f"HTTP {response.status_code} {body}"
            )

        evidence = [PageEvidence.model_validate(item) for item in body.get("evidence", [])]
        evidence_pages = [(item.paper_id, item.page_number) for item in evidence]
        expected_pages = {page_key(item) for item in row["expected_pages"]}
        must_cite_pages = {page_key(item) for item in row["must_cite_pages"]}
        should_refuse = bool(row["should_refuse"])

        recall_by_k = {}
        for k in (1, 3, 5):
            top_k_pages = set(evidence_pages[:k])
            recall_by_k[f"recall_at_{k}"] = (
                len(expected_pages.intersection(top_k_pages)) / len(expected_pages)
                if expected_pages
                else None
            )

        citation_page_correct = (
            must_cite_pages.issubset(set(evidence_pages[:5]))
            if must_cite_pages and not should_refuse
            else None
        )
        refusal_correct = (len(evidence_pages) == 0) if should_refuse else None

        evaluated.append(
            {
                "id": row.get("id"),
                "question": row["question"],
                "question_type": row["question_type"],
                "library_id": row.get("library_id"),
                "group_id": row.get("group_id"),
                "provenance": row.get("provenance"),
                "paper_ids": row["paper_ids"],
                "expected_pages": [format_page_key(item) for item in sorted(expected_pages)],
                "must_cite_pages": [format_page_key(item) for item in sorted(must_cite_pages)],
                "answer_key": row["answer_key"],
                "should_refuse": should_refuse,
                "status": body.get("status"),
                "limits": body.get("limits", []),
                "note": body.get("note"),
                "evidence_count": len(evidence_pages),
                "evidence_pages": [format_page_key(item) for item in evidence_pages],
                "top_evidence": [item.model_dump(mode="json") for item in evidence[:5]],
                "recall_at_1": recall_by_k["recall_at_1"],
                "recall_at_3": recall_by_k["recall_at_3"],
                "recall_at_5": recall_by_k["recall_at_5"],
                "citation_page_correct": citation_page_correct,
                "refusal_correct": refusal_correct,
            }
        )
    return evaluated


def evaluate_bm25_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    retriever = TextRetriever.from_manifests(build_synthetic_text_manifests())
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        hits = retriever.search(row["question"], paper_ids=row["paper_ids"], top_k=5)
        evidence_pages = [(item.paper_id, item.page_number) for item in hits]
        expected_pages = {page_key(item) for item in row["expected_pages"]}
        must_cite_pages = {page_key(item) for item in row["must_cite_pages"]}
        should_refuse = bool(row["should_refuse"])

        recall_by_k = {}
        for k in (1, 3, 5):
            top_k_pages = set(evidence_pages[:k])
            recall_by_k[f"recall_at_{k}"] = (
                len(expected_pages.intersection(top_k_pages)) / len(expected_pages)
                if expected_pages
                else None
            )

        citation_page_correct = (
            must_cite_pages.issubset(set(evidence_pages[:5]))
            if must_cite_pages and not should_refuse
            else None
        )
        refusal_correct = (len(evidence_pages) == 0) if should_refuse else None

        evaluated.append(
            {
                "id": row.get("id"),
                "question": row["question"],
                "question_type": row["question_type"],
                "library_id": row.get("library_id"),
                "group_id": row.get("group_id"),
                "provenance": row.get("provenance"),
                "paper_ids": row["paper_ids"],
                "expected_pages": [format_page_key(item) for item in sorted(expected_pages)],
                "must_cite_pages": [format_page_key(item) for item in sorted(must_cite_pages)],
                "answer_key": row["answer_key"],
                "should_refuse": should_refuse,
                "status": "success" if hits else "partial",
                "limits": [] if hits else ["No BM25 text evidence retrieved."],
                "note": BM25_SYNTHETIC_BOUNDARY,
                "evidence_count": len(evidence_pages),
                "evidence_pages": [format_page_key(item) for item in evidence_pages],
                "top_evidence": [item.model_dump(mode="json") for item in hits],
                "recall_at_1": recall_by_k["recall_at_1"],
                "recall_at_3": recall_by_k["recall_at_3"],
                "recall_at_5": recall_by_k["recall_at_5"],
                "citation_page_correct": citation_page_correct,
                "refusal_correct": refusal_correct,
            }
        )
    return evaluated


def keyword_overlap_hits(row: dict[str, Any], top_k: int = 5) -> list[dict[str, Any]]:
    paper_ids = {str(paper_id) for paper_id in row["paper_ids"]}
    if not paper_ids:
        return []

    question_tokens = set(TOKEN_RE.findall(row["question"].lower()))
    scored: list[tuple[int, SyntheticPage]] = []
    for page in synthetic_pages():
        if page.paper_id not in paper_ids:
            continue
        page_tokens = set(TOKEN_RE.findall(f"{page.title} {page.caption}".lower()))
        overlap = len(question_tokens.intersection(page_tokens))
        if overlap > 0:
            scored.append((overlap, page))

    scored.sort(key=lambda item: (-item[0], item[1].paper_id, item[1].page_number))
    return [
        {
            "paper_id": page.paper_id,
            "page_number": page.page_number,
            "title": page.title,
            "caption": page.caption,
            "score": overlap,
            "source": "keyword_overlap",
        }
        for overlap, page in scored[:top_k]
    ]


def evaluate_keyword_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        hits = keyword_overlap_hits(row)
        evidence_pages = [(str(item["paper_id"]), int(item["page_number"])) for item in hits]
        expected_pages = {page_key(item) for item in row["expected_pages"]}
        must_cite_pages = {page_key(item) for item in row["must_cite_pages"]}
        should_refuse = bool(row["should_refuse"])

        recall_by_k = {}
        for k in (1, 3, 5):
            top_k_pages = set(evidence_pages[:k])
            recall_by_k[f"recall_at_{k}"] = (
                len(expected_pages.intersection(top_k_pages)) / len(expected_pages)
                if expected_pages
                else None
            )

        citation_page_correct = (
            must_cite_pages.issubset(set(evidence_pages[:5]))
            if must_cite_pages and not should_refuse
            else None
        )
        refusal_correct = (len(evidence_pages) == 0) if should_refuse else None

        evaluated.append(
            {
                "id": row.get("id"),
                "question": row["question"],
                "question_type": row["question_type"],
                "library_id": row.get("library_id"),
                "group_id": row.get("group_id"),
                "provenance": row.get("provenance"),
                "paper_ids": row["paper_ids"],
                "expected_pages": [format_page_key(item) for item in sorted(expected_pages)],
                "must_cite_pages": [format_page_key(item) for item in sorted(must_cite_pages)],
                "answer_key": row["answer_key"],
                "should_refuse": should_refuse,
                "status": "success" if hits else "partial",
                "limits": [] if hits else ["No keyword overlap evidence retrieved."],
                "note": KEYWORD_SYNTHETIC_BOUNDARY,
                "evidence_count": len(evidence_pages),
                "evidence_pages": [format_page_key(item) for item in evidence_pages],
                "top_evidence": hits,
                "recall_at_1": recall_by_k["recall_at_1"],
                "recall_at_3": recall_by_k["recall_at_3"],
                "recall_at_5": recall_by_k["recall_at_5"],
                "citation_page_correct": citation_page_correct,
                "refusal_correct": refusal_correct,
            }
        )
    return evaluated


def evaluate_hybrid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return asyncio.run(_evaluate_hybrid_rows(rows))


async def _evaluate_hybrid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vector_store = await build_synthetic_vector_store()
    service = HybridRetrievalService(
        visrag=SyntheticVisRAG(),  # type: ignore[arg-type]
        vector_store=vector_store,
        manifest_store=SyntheticTextManifestStore(build_synthetic_text_manifests()),  # type: ignore[arg-type]
    )
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        result = await service.search(
            query=row["question"],
            paper_ids=row["paper_ids"],
            top_k=5,
        )
        evidence_pages = [(item.paper_id, item.page_number) for item in result.evidence]
        expected_pages = {page_key(item) for item in row["expected_pages"]}
        must_cite_pages = {page_key(item) for item in row["must_cite_pages"]}
        should_refuse = bool(row["should_refuse"])
        packet_units = [unit.model_dump(mode="json") for unit in result.evidence_packet.units]

        recall_by_k = {}
        for k in (1, 3, 5):
            top_k_pages = set(evidence_pages[:k])
            recall_by_k[f"recall_at_{k}"] = (
                len(expected_pages.intersection(top_k_pages)) / len(expected_pages)
                if expected_pages
                else None
            )

        citation_page_correct = (
            must_cite_pages.issubset(set(evidence_pages[:5]))
            if must_cite_pages and not should_refuse
            else None
        )
        refusal_correct = (len(evidence_pages) == 0) if should_refuse else None

        evaluated.append(
            {
                "id": row.get("id"),
                "question": row["question"],
                "question_type": row["question_type"],
                "library_id": row.get("library_id"),
                "group_id": row.get("group_id"),
                "provenance": row.get("provenance"),
                "paper_ids": row["paper_ids"],
                "expected_pages": [format_page_key(item) for item in sorted(expected_pages)],
                "must_cite_pages": [format_page_key(item) for item in sorted(must_cite_pages)],
                "answer_key": row["answer_key"],
                "should_refuse": should_refuse,
                "status": result.status,
                "limits": result.limits,
                "note": HYBRID_SYNTHETIC_BOUNDARY,
                "evidence_count": len(evidence_pages),
                "evidence_pages": [format_page_key(item) for item in evidence_pages],
                "top_evidence": [item.model_dump(mode="json") for item in result.evidence[:5]],
                "top_evidence_packet_units": packet_units[:5],
                "source_coverage": source_coverage_counts(packet_units),
                "recall_at_1": recall_by_k["recall_at_1"],
                "recall_at_3": recall_by_k["recall_at_3"],
                "recall_at_5": recall_by_k["recall_at_5"],
                "citation_page_correct": citation_page_correct,
                "refusal_correct": refusal_correct,
            }
        )
    return evaluated


def source_coverage_counts(units: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "visual_trace_units": 0,
        "text_trace_units": 0,
        "hybrid_trace_units": 0,
        "visual_only_units": 0,
        "text_only_units": 0,
    }
    for unit in units:
        retrievers = {
            str(trace.get("retriever"))
            for trace in unit.get("rank_trace", [])
            if trace.get("retriever")
        }
        if "visrag" in retrievers:
            counts["visual_trace_units"] += 1
        if "bm25" in retrievers:
            counts["text_trace_units"] += 1
        if {"visrag", "bm25"}.issubset(retrievers):
            counts["hybrid_trace_units"] += 1
        elif retrievers == {"visrag"}:
            counts["visual_only_units"] += 1
        elif retrievers == {"bm25"}:
            counts["text_only_units"] += 1
    return counts


def aggregate_source_coverage(evaluated: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "visual_trace_units": 0,
        "text_trace_units": 0,
        "hybrid_trace_units": 0,
        "visual_only_units": 0,
        "text_only_units": 0,
    }
    for row in evaluated:
        for key, value in row.get("source_coverage", {}).items():
            totals[key] = totals.get(key, 0) + int(value)
    return totals


def aggregate_metrics(evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    positive_rows = [row for row in evaluated if not row["should_refuse"]]
    refusal_rows = [row for row in evaluated if row["should_refuse"]]
    citation_rows = [row for row in positive_rows if row["citation_page_correct"] is not None]

    metrics: dict[str, Any] = {
        "question_count": len(evaluated),
        "positive_question_count": len(positive_rows),
        "refusal_question_count": len(refusal_rows),
        "negative_case_share": len(refusal_rows) / len(evaluated) if evaluated else 0.0,
    }
    for k in (1, 3, 5):
        key = f"recall_at_{k}"
        values = [float(row[key]) for row in positive_rows if row[key] is not None]
        metrics[f"Recall@{k}"] = sum(values) / len(values) if values else 0.0

    citation_values = [bool(row["citation_page_correct"]) for row in citation_rows]
    metrics["citation_page_correctness"] = (
        sum(1 for value in citation_values if value) / len(citation_values)
        if citation_values
        else 0.0
    )
    refusal_values = [bool(row["refusal_correct"]) for row in refusal_rows]
    metrics["refusal_correctness"] = (
        sum(1 for value in refusal_values if value) / len(refusal_values)
        if refusal_values
        else 0.0
    )
    return metrics


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generated_at_for(path: Path) -> str:
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8")).get("generated_at")
        except json.JSONDecodeError:
            existing = None
        if isinstance(existing, str) and existing:
            return existing
    return datetime.now(timezone.utc).isoformat()


def write_csv(
    path: Path,
    evaluated: list[dict[str, Any]],
    *,
    boundary: str = SYNTHETIC_BOUNDARY,
) -> None:
    fieldnames = [
        "id",
        "question_type",
        "library_id",
        "group_id",
        "should_refuse",
        "mode_boundary",
        "paper_ids",
        "expected_pages",
        "must_cite_pages",
        "evidence_pages",
        "recall_at_1",
        "recall_at_3",
        "recall_at_5",
        "citation_page_correct",
        "refusal_correct",
        "status",
        "evidence_count",
        "limits",
        "question",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in evaluated:
            writer.writerow(
                {
                    key: boundary
                    if key == "mode_boundary"
                    else ";".join(str(item) for item in row[key])
                    if isinstance(row.get(key), list)
                    else row.get(key)
                    for key in fieldnames
                }
            )


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def md_bool(value: bool | None) -> str:
    if value is None:
        return "n/a"
    return "yes" if value else "no"


def write_markdown(
    path: Path,
    payload: dict[str, Any],
) -> None:
    metrics = payload["metrics"]
    rows = payload["questions"]
    lines = [
        "# Node 1 Retrieval Baseline",
        "",
        "Mode: synthetic smoke corpus.",
        "",
        "This run exercises the current FastAPI `POST /retrieval/search` route through "
        "`TestClient` dependency overrides. It seeds a deterministic page-level corpus "
        "through the current `VectorStore.upsert_page` and `VectorStore.search_pages` "
        "interfaces using an in-memory Qdrant-compatible client. This is not a real-PDF, "
        "real-VisRAG, or real-local-corpus benchmark.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Questions | {metrics['question_count']} |",
        f"| Negative/refusal share | {pct(metrics['negative_case_share'])} |",
        f"| Recall@1 | {pct(metrics['Recall@1'])} |",
        f"| Recall@3 | {pct(metrics['Recall@3'])} |",
        f"| Recall@5 | {pct(metrics['Recall@5'])} |",
        f"| Citation-page correctness | {pct(metrics['citation_page_correctness'])} |",
        f"| Refusal correctness | {pct(metrics['refusal_correctness'])} |",
        "",
        "## Per-Question Results",
        "",
        "| ID | Type | Expected | Top evidence | R@5 | Cite pages correct | Refusal correct |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {id} | {question_type} | {expected} | {evidence} | {recall} | {cite} | {refusal} |".format(
                id=row["id"],
                question_type=row["question_type"],
                expected=", ".join(row["expected_pages"]) or "n/a",
                evidence=", ".join(row["evidence_pages"][:5]) or "none",
                recall=pct(row["recall_at_5"]),
                cite=md_bool(row["citation_page_correct"]),
                refusal=md_bool(row["refusal_correct"]),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Synthetic paper IDs are stable aliases such as `demo-visrag-core` and `demo-bm25-text`.",
            "- `library_id` and `group_id` are recorded in the fixture to match the current Paper Manager scope model.",
            "- Refusal correctness means retrieval returned no evidence for a refusal row. It is not answer-level refusal generation.",
            "- Scoped hard negatives may still retrieve unrelated pages because the current raw vector route has no semantic abstention gate.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report_metrics(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    lines = [
        "# Baseline Retrieval Metrics",
        "",
        "## Methods And Evaluation Setup",
        "",
        "| Field | Node 1 setup |",
        "| --- | --- |",
        "| Evaluation surface | Current FastAPI `POST /retrieval/search` route |",
        "| Corpus mode | Synthetic smoke corpus because no real local PDFs are present under `storage/papers/` |",
        "| Corpus size | 4 synthetic papers, 12 synthetic pages |",
        "| Question set | 12 golden questions, including 3 refusal/negative cases (25.0%) |",
        "| Scope fields | Fixture rows include `paper_ids`, optional `library_id`, `group_id`, and provenance |",
        "| Retrieval path | `TestClient` plus dependency overrides; synthetic query embeddings; current `VectorStore` page upsert/search interface; in-memory Qdrant-compatible client |",
        "| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness |",
        "| Citation grain | Page-level `(paper_id, page_number)` correctness only |",
        "",
        "## First Baseline Row",
        "",
        "| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Boundary |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        (
            f"| {payload['output_prefix']} | synthetic smoke corpus | "
            f"{pct(metrics['Recall@1'])} | {pct(metrics['Recall@3'])} | {pct(metrics['Recall@5'])} | "
            f"{pct(metrics['citation_page_correctness'])} | {pct(metrics['refusal_correctness'])} | "
            "Not a real-PDF, real-VisRAG, or real-local-corpus benchmark |"
        ),
        "",
        "## Limitations",
        "",
        "- No real local PDF corpus was present under `storage/papers/`, so Node 1 is not a real-PDF or real-local-corpus benchmark.",
        "- Synthetic page captions stand in for rendered page evidence; this is not a real-VisRAG benchmark and real VisRAG model quality is not measured.",
        "- Refusal correctness is retrieval-level no-evidence behavior, not generated answer refusal.",
        "- The current raw retrieval route can return low-similarity pages for scoped hard negatives when no score threshold is used; later nodes should add calibrated evidence sufficiency gates before making answer-level claims.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_bm25_markdown(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    rows = payload["questions"]
    lines = [
        "# Node 4 BM25 Text Baseline",
        "",
        "Mode: synthetic BM25-only text-manifest corpus.",
        "",
        "This run builds synthetic `TextManifest` objects aligned to the Node 1 golden "
        "fixture paper/page IDs and calls `TextRetriever` directly. It does not call "
        "VisRAG, Qdrant, `/retrieval/search`, chat, hybrid fusion, or RRF.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Questions | {metrics['question_count']} |",
        f"| Negative/refusal share | {pct(metrics['negative_case_share'])} |",
        f"| Recall@1 | {pct(metrics['Recall@1'])} |",
        f"| Recall@3 | {pct(metrics['Recall@3'])} |",
        f"| Recall@5 | {pct(metrics['Recall@5'])} |",
        f"| Citation-page correctness | {pct(metrics['citation_page_correctness'])} |",
        f"| Refusal correctness | {pct(metrics['refusal_correctness'])} |",
        "",
        "## Per-Question Results",
        "",
        "| ID | Type | Expected | BM25 top pages | R@5 | Cite pages correct | Refusal correct |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {id} | {question_type} | {expected} | {evidence} | {recall} | {cite} | {refusal} |".format(
                id=row["id"],
                question_type=row["question_type"],
                expected=", ".join(row["expected_pages"]) or "n/a",
                evidence=", ".join(row["evidence_pages"][:5]) or "none",
                recall=pct(row["recall_at_5"]),
                cite=md_bool(row["citation_page_correct"]),
                refusal=md_bool(row["refusal_correct"]),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- BM25 scores are lexical text scores from `TextRetriever`; they are not visual scores.",
            "- Synthetic text pages are derived from the existing golden fixture captions and titles.",
            "- Refusal correctness means BM25 returned no page hits for a refusal row. It is not answer-level refusal generation.",
            "- Node 5 remains responsible for page-canonical hybrid/RRF fusion.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_bm25_report_metrics(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    lines = [
        "# BM25 Text Retrieval Metrics",
        "",
        "## Methods And Evaluation Setup",
        "",
        "| Field | Node 4 setup |",
        "| --- | --- |",
        "| Evaluation surface | Direct `TextRetriever` over synthetic Node 3 `TextManifest` objects |",
        "| Corpus mode | Synthetic text-manifest corpus aligned to the existing golden fixture paper/page IDs |",
        "| Corpus size | 4 synthetic papers, 12 synthetic pages |",
        "| Question set | 12 golden questions, including 3 refusal/negative cases (25.0%) |",
        "| Retrieval path | Local deterministic BM25 only; no FastAPI route, VisRAG, Qdrant, chat, hybrid fusion, or RRF |",
        "| BM25 parameters | `k1=1.5`, `b=0.75` |",
        "| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness |",
        "| Citation grain | Page-level `(paper_id, page_number)` correctness only |",
        "",
        "## BM25 Baseline Row",
        "",
        "| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Boundary |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        (
            f"| {payload['output_prefix']} | synthetic BM25-only text manifest | "
            f"{pct(metrics['Recall@1'])} | {pct(metrics['Recall@3'])} | {pct(metrics['Recall@5'])} | "
            f"{pct(metrics['citation_page_correctness'])} | {pct(metrics['refusal_correctness'])} | "
            "Not a real-PDF, real-corpus, hybrid, RRF, or VisRAG benchmark |"
        ),
        "",
        "## Interpretation",
        "",
        "- BM25 provides an explainable exact-term page retriever for text-bearing pages from Node 3 manifests.",
        "- BM25 is useful for method names, dataset names, abbreviations, and citation-like tokens when selectable text exists.",
        "- BM25 does not replace the current visual `/retrieval/search` route in Node 4.",
        "- This row is a synthetic measurement artifact for report/demo progress, not a claim of real local corpus quality.",
        "",
        "## Limitations",
        "",
        "- The synthetic text corpus is title/caption based and does not measure real PyMuPDF extraction quality.",
        "- Refusal correctness is retrieval-level no-hit behavior; answer-level abstention is still later orchestration work.",
        "- Hybrid page-canonical fusion is explicitly deferred to Node 5.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_keyword_markdown(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    rows = payload["questions"]
    lines = [
        "# Keyword Overlap Baseline",
        "",
        "Mode: deterministic keyword overlap over synthetic fixture pages.",
        "",
        "This run tokenizes each golden question and each allowed synthetic page title "
        "plus caption with `TOKEN_RE`, scores pages by unique token overlap count, and "
        "sorts by descending overlap, then `paper_id`, then `page_number`. It is not an "
        "LLM baseline, BM25 baseline, VisRAG result, real-PDF result, or real-corpus benchmark.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Questions | {metrics['question_count']} |",
        f"| Negative/refusal share | {pct(metrics['negative_case_share'])} |",
        f"| Recall@1 | {pct(metrics['Recall@1'])} |",
        f"| Recall@3 | {pct(metrics['Recall@3'])} |",
        f"| Recall@5 | {pct(metrics['Recall@5'])} |",
        f"| Citation-page correctness | {pct(metrics['citation_page_correctness'])} |",
        f"| Refusal correctness | {pct(metrics['refusal_correctness'])} |",
        "",
        "## Per-Question Results",
        "",
        "| ID | Type | Expected | Keyword top pages | R@5 | Cite pages correct | Refusal correct |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {id} | {question_type} | {expected} | {evidence} | {recall} | {cite} | {refusal} |".format(
                id=row["id"],
                question_type=row["question_type"],
                expected=", ".join(row["expected_pages"]) or "n/a",
                evidence=", ".join(row["evidence_pages"][:5]) or "none",
                recall=pct(row["recall_at_5"]),
                cite=md_bool(row["citation_page_correct"]),
                refusal=md_bool(row["refusal_correct"]),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Keyword scoring is exact token overlap, not BM25 term weighting or semantic retrieval.",
            "- The corpus is the existing synthetic fixture pages from `synthetic_pages()`.",
            "- The question set is `eval/retrieval/golden_questions.jsonl`.",
            "- If `paper_ids` is empty, or no allowed page has positive overlap, the baseline returns no pages.",
            "- Refusal correctness is retrieval-level no-hit behavior, not answer-level refusal generation.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_keyword_report_metrics(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    lines = [
        "# Keyword Overlap Baseline Metrics",
        "",
        "## Methods And Evaluation Setup",
        "",
        "| Field | Keyword baseline setup |",
        "| --- | --- |",
        "| Evaluation surface | Deterministic local function in `eval/retrieval/run_retrieval_eval.py` |",
        "| Corpus mode | Existing synthetic pages from `synthetic_pages()` |",
        "| Corpus size | 4 synthetic papers, 12 synthetic pages |",
        "| Question set | 12 golden questions from `eval/retrieval/golden_questions.jsonl`, including 3 refusal/negative cases (25.0%) |",
        "| Retrieval path | Tokenize question and page title+caption with `TOKEN_RE`; score by unique token overlap; tie-break by `paper_id`, then `page_number` |",
        "| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness |",
        "| Citation grain | Page-level `(paper_id, page_number)` correctness only |",
        "",
        "## Keyword Baseline Row",
        "",
        "| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Boundary |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        (
            f"| {payload['output_prefix']} | keyword overlap baseline | "
            f"{pct(metrics['Recall@1'])} | {pct(metrics['Recall@3'])} | {pct(metrics['Recall@5'])} | "
            f"{pct(metrics['citation_page_correctness'])} | {pct(metrics['refusal_correctness'])} | "
            "Not an LLM, BM25, VisRAG, real-PDF, or real-corpus benchmark |"
        ),
        "",
        "## Limitations",
        "",
        "- This is a weak deterministic same-fixture comparator, not a model or production retriever.",
        "- It measures only title/caption token overlap on the synthetic fixture.",
        "- It returns no pages for empty paper scope or zero positive overlap.",
        "- Refusal correctness is retrieval-level no-hit behavior; answer-level abstention is outside this run.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_hybrid_markdown(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    rows = payload["questions"]
    coverage = metrics["source_coverage_counts"]
    lines = [
        "# Node 5 Hybrid Retrieval Baseline",
        "",
        "Mode: synthetic hybrid fixture baseline.",
        "",
        "This run calls `HybridRetrievalService` directly with the synthetic VisRAG "
        "vector store and synthetic Node 3 text manifests. It fuses page-level visual "
        "and BM25 ranks with RRF at canonical `(paper_id, page_number)` grain. This is "
        "not a real-PDF, real-corpus, or real-corpus improvement benchmark.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Questions | {metrics['question_count']} |",
        f"| Negative/refusal share | {pct(metrics['negative_case_share'])} |",
        f"| Recall@1 | {pct(metrics['Recall@1'])} |",
        f"| Recall@3 | {pct(metrics['Recall@3'])} |",
        f"| Recall@5 | {pct(metrics['Recall@5'])} |",
        f"| Citation-page correctness | {pct(metrics['citation_page_correctness'])} |",
        f"| Refusal correctness | {pct(metrics['refusal_correctness'])} |",
        f"| Units with both traces | {coverage['hybrid_trace_units']} |",
        f"| Visual-only units | {coverage['visual_only_units']} |",
        f"| Text-only units | {coverage['text_only_units']} |",
        "",
        "## Per-Question Results",
        "",
        "| ID | Type | Expected | Hybrid top pages | R@5 | Cite pages correct | Refusal correct | Source coverage |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        row_coverage = row["source_coverage"]
        coverage_text = (
            f"both={row_coverage['hybrid_trace_units']}; "
            f"visual_only={row_coverage['visual_only_units']}; "
            f"text_only={row_coverage['text_only_units']}"
        )
        lines.append(
            "| {id} | {question_type} | {expected} | {evidence} | {recall} | {cite} | {refusal} | {coverage} |".format(
                id=row["id"],
                question_type=row["question_type"],
                expected=", ".join(row["expected_pages"]) or "n/a",
                evidence=", ".join(row["evidence_pages"][:5]) or "none",
                recall=pct(row["recall_at_5"]),
                cite=md_bool(row["citation_page_correct"]),
                refusal=md_bool(row["refusal_correct"]),
                coverage=coverage_text,
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Hybrid scores are RRF scores from source ranks with `k=60`, not calibrated relevance probabilities.",
            "- Source traces preserve visual and BM25 source ranks and raw scores inside `EvidencePacket.units[].rank_trace`.",
            "- This is a synthetic fixture baseline over stable aliases and fixture captions, not a real-corpus improvement claim.",
            "- Chat/context/UI consumption remains deferred to Node 6.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_hybrid_report_metrics(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    coverage = metrics["source_coverage_counts"]
    lines = [
        "# Hybrid Retrieval Metrics",
        "",
        "## Methods And Evaluation Setup",
        "",
        "| Field | Node 5 setup |",
        "| --- | --- |",
        "| Evaluation surface | Direct `HybridRetrievalService` over synthetic fixtures |",
        "| Corpus mode | Synthetic fixture baseline aligned to the existing golden paper/page IDs |",
        "| Corpus size | 4 synthetic papers, 12 synthetic pages |",
        "| Question set | 12 golden questions, including 3 refusal/negative cases (25.0%) |",
        "| Retrieval path | Synthetic VisRAG vector store plus synthetic Node 3 `TextManifest` objects; page-canonical RRF fusion with `k=60` |",
        "| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness, source coverage counts |",
        "| Citation grain | Page-level `(paper_id, page_number)` correctness only |",
        "",
        "## Hybrid Baseline Row",
        "",
        "| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Both-trace units | Boundary |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        (
            f"| {payload['output_prefix']} | synthetic hybrid fixture baseline | "
            f"{pct(metrics['Recall@1'])} | {pct(metrics['Recall@3'])} | {pct(metrics['Recall@5'])} | "
            f"{pct(metrics['citation_page_correctness'])} | {pct(metrics['refusal_correctness'])} | "
            f"{coverage['hybrid_trace_units']} | Not a real-PDF, real-corpus, or real-corpus improvement benchmark |"
        ),
        "",
        "## Source Coverage",
        "",
        "| Coverage type | Unit count |",
        "| --- | ---: |",
        f"| Units with visual traces | {coverage['visual_trace_units']} |",
        f"| Units with BM25 traces | {coverage['text_trace_units']} |",
        f"| Units with both visual and BM25 traces | {coverage['hybrid_trace_units']} |",
        f"| Visual-only units | {coverage['visual_only_units']} |",
        f"| Text-only units | {coverage['text_only_units']} |",
        "",
        "## Interpretation",
        "",
        "- Node 5 proves the additive page-canonical fusion path and provenance contract on fixtures.",
        "- Overlapping pages collapse into one `hybrid_page` evidence unit with both source traces.",
        "- The row is report/demo evidence for the retrieval contract only; it is not a real local corpus quality result.",
        "",
        "## Limitations",
        "",
        "- Synthetic captions and text manifests do not measure real PyMuPDF extraction or VisRAG embedding quality.",
        "- Refusal correctness is retrieval-level no-hit behavior; answer-level abstention remains Node 6/7 work.",
        "- No chat, UI, or multi-pass orchestration behavior is included in this node.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(output_prefix: str, rows: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": RESULTS_DIR / f"{output_prefix}.json",
        "csv": RESULTS_DIR / f"{output_prefix}.csv",
        "markdown": RESULTS_DIR / f"{output_prefix}.md",
        "report": REPORT_METRICS_PATH,
    }
    generated_at = generated_at_for(paths["json"])
    payload = {
        "output_prefix": output_prefix,
        "generated_at": generated_at,
        "mode": "synthetic",
        "boundary": SYNTHETIC_BOUNDARY,
        "corpus": [
            {
                "paper_id": page.paper_id,
                "page_number": page.page_number,
                "title": page.title,
                "group_id": page.group_id,
            }
            for page in synthetic_pages()
        ],
        "metrics": metrics,
        "questions": rows,
    }
    write_json(paths["json"], payload)
    write_csv(paths["csv"], rows)
    write_markdown(paths["markdown"], payload)
    write_report_metrics(paths["report"], payload)
    return paths


def write_bm25_outputs(
    output_prefix: str,
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> dict[str, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": RESULTS_DIR / f"{output_prefix}.json",
        "csv": RESULTS_DIR / f"{output_prefix}.csv",
        "markdown": RESULTS_DIR / f"{output_prefix}.md",
        "report": BM25_REPORT_METRICS_PATH,
    }
    generated_at = generated_at_for(paths["json"])
    payload = {
        "output_prefix": output_prefix,
        "generated_at": generated_at,
        "mode": "bm25-synthetic",
        "boundary": BM25_SYNTHETIC_BOUNDARY,
        "retriever": {
            "name": "TextRetriever",
            "source": "bm25_text",
            "k1": 1.5,
            "b": 0.75,
        },
        "corpus": [
            {
                "paper_id": page.paper_id,
                "page_number": page.page_number,
                "title": page.title,
                "group_id": page.group_id,
            }
            for page in synthetic_pages()
        ],
        "metrics": metrics,
        "questions": rows,
    }
    write_json(paths["json"], payload)
    write_csv(paths["csv"], rows, boundary=BM25_SYNTHETIC_BOUNDARY)
    write_bm25_markdown(paths["markdown"], payload)
    write_bm25_report_metrics(paths["report"], payload)
    return paths


def write_keyword_outputs(
    output_prefix: str,
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> dict[str, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": RESULTS_DIR / f"{output_prefix}.json",
        "csv": RESULTS_DIR / f"{output_prefix}.csv",
        "markdown": RESULTS_DIR / f"{output_prefix}.md",
        "report": KEYWORD_REPORT_METRICS_PATH,
    }
    generated_at = generated_at_for(paths["json"])
    payload = {
        "output_prefix": output_prefix,
        "generated_at": generated_at,
        "mode": "keyword-synthetic",
        "boundary": KEYWORD_SYNTHETIC_BOUNDARY,
        "retriever": {
            "name": "keyword_overlap",
            "source": "synthetic_page_title_caption",
            "tokenizer": "TOKEN_RE",
            "score": "unique_question_page_token_overlap_count",
            "tie_break": ["paper_id", "page_number"],
        },
        "corpus": [
            {
                "paper_id": page.paper_id,
                "page_number": page.page_number,
                "title": page.title,
                "group_id": page.group_id,
            }
            for page in synthetic_pages()
        ],
        "metrics": metrics,
        "questions": rows,
    }
    write_json(paths["json"], payload)
    write_csv(paths["csv"], rows, boundary=KEYWORD_SYNTHETIC_BOUNDARY)
    write_keyword_markdown(paths["markdown"], payload)
    write_keyword_report_metrics(paths["report"], payload)
    return paths


def write_hybrid_outputs(
    output_prefix: str,
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> dict[str, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": RESULTS_DIR / f"{output_prefix}.json",
        "csv": RESULTS_DIR / f"{output_prefix}.csv",
        "markdown": RESULTS_DIR / f"{output_prefix}.md",
        "report": HYBRID_REPORT_METRICS_PATH,
    }
    generated_at = generated_at_for(paths["json"])
    hybrid_metrics = dict(metrics)
    hybrid_metrics["source_coverage_counts"] = aggregate_source_coverage(rows)
    payload = {
        "output_prefix": output_prefix,
        "generated_at": generated_at,
        "mode": "hybrid-synthetic",
        "boundary": HYBRID_SYNTHETIC_BOUNDARY,
        "retriever": {
            "name": "HybridRetrievalService",
            "source": "hybrid_page",
            "rrf_k": 60,
            "fusion_key": ["paper_id", "page_number"],
        },
        "corpus": [
            {
                "paper_id": page.paper_id,
                "page_number": page.page_number,
                "title": page.title,
                "group_id": page.group_id,
            }
            for page in synthetic_pages()
        ],
        "metrics": hybrid_metrics,
        "questions": rows,
    }
    write_json(paths["json"], payload)
    write_csv(paths["csv"], rows, boundary=HYBRID_SYNTHETIC_BOUNDARY)
    write_hybrid_markdown(paths["markdown"], payload)
    write_hybrid_report_metrics(paths["report"], payload)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PaperMemory retrieval golden eval.")
    parser.add_argument(
        "--mode",
        choices=["synthetic", "bm25-synthetic", "hybrid-synthetic", "keyword-synthetic"],
        default="synthetic",
        help=(
            "Evaluation mode. Use synthetic for the current visual/API smoke corpus "
            "bm25-synthetic for the Node 4 text-manifest BM25 baseline, "
            "hybrid-synthetic for the Node 5 fixture hybrid baseline, "
            "or keyword-synthetic for a deterministic same-fixture keyword overlap baseline."
        ),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=FIXTURE_PATH,
        help="JSONL golden question fixture.",
    )
    parser.add_argument(
        "--output-prefix",
        default="node1-baseline",
        help="Prefix for JSON, CSV, and Markdown files under eval/retrieval/results/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_fixture(args.fixture)
    if not 10 <= len(rows) <= 15:
        raise ValueError(f"expected 10-15 golden questions, found {len(rows)}")
    refusal_count = sum(1 for row in rows if row["should_refuse"])
    refusal_share = refusal_count / len(rows)
    if not 0.20 <= refusal_share <= 0.30:
        raise ValueError(f"expected 20-30% refusal cases, found {refusal_share:.1%}")

    if args.mode == "bm25-synthetic":
        evaluated = evaluate_bm25_rows(rows)
        metrics = aggregate_metrics(evaluated)
        paths = write_bm25_outputs(args.output_prefix, evaluated, metrics)
    elif args.mode == "keyword-synthetic":
        evaluated = evaluate_keyword_rows(rows)
        metrics = aggregate_metrics(evaluated)
        paths = write_keyword_outputs(args.output_prefix, evaluated, metrics)
    elif args.mode == "hybrid-synthetic":
        evaluated = evaluate_hybrid_rows(rows)
        metrics = aggregate_metrics(evaluated)
        paths = write_hybrid_outputs(args.output_prefix, evaluated, metrics)
    else:
        client = build_synthetic_client()
        evaluated = evaluate_rows(client, rows)
        metrics = aggregate_metrics(evaluated)
        paths = write_outputs(args.output_prefix, evaluated, metrics)
    print(
        "Wrote retrieval eval outputs: "
        + ", ".join(f"{name}={path}" for name, path in paths.items())
    )
    print(
        "Metrics: "
        f"Recall@1={metrics['Recall@1']:.3f}, "
        f"Recall@3={metrics['Recall@3']:.3f}, "
        f"Recall@5={metrics['Recall@5']:.3f}, "
        f"citation_page_correctness={metrics['citation_page_correctness']:.3f}, "
        f"refusal_correctness={metrics['refusal_correctness']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
