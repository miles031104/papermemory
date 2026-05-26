import asyncio
from io import BytesIO
from pathlib import Path
from typing import Sequence

import pytest
from fastapi import HTTPException, UploadFile

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.schemas.papers import PaperMetadata, PaperStatus
from app.services.ingestion_service import IngestionService


class FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def render_pages(self, pdf_path: Path, output_dir: Path) -> list[Path]:
        self.calls.append((pdf_path, output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        page_paths = [output_dir / "page-0001.png", output_dir / "page-0002.png"]
        for page_path in page_paths:
            page_path.write_bytes(b"fake image")
        return page_paths


class FakeIndexer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[Path]]] = []

    async def index_pages(self, paper_id: str, page_paths: Sequence[Path], captions=None) -> None:
        paths = list(page_paths)
        assert all(path.exists() for path in paths)
        self.calls.append((paper_id, paths))


class FailingIndexer:
    async def index_pages(self, paper_id: str, page_paths: Sequence[Path], captions=None) -> None:
        _ = (paper_id, page_paths)
        raise RuntimeError("qdrant unavailable")


def test_upload_renders_then_indexes_and_marks_ready(tmp_path: Path) -> None:
    renderer = FakeRenderer()
    indexer = FakeIndexer()
    service = IngestionService(
        paths=StoragePaths(Settings(storage_root=tmp_path)),
        renderer=renderer,
        indexing_service=indexer,
    )
    upload = UploadFile(filename="paper.pdf", file=BytesIO(b"%PDF-1.7\n"))

    paper = asyncio.run(service.accept_pdf_upload(file=upload, title="VisRAG Paper"))

    assert paper.status == PaperStatus.ready
    assert paper.page_count == 2
    assert len(renderer.calls) == 1
    assert len(indexer.calls) == 1
    assert indexer.calls[0][0] == paper.paper_id
    assert indexer.calls[0][1] == [
        tmp_path / "rendered_pages" / paper.paper_id / "page-0001.png",
        tmp_path / "rendered_pages" / paper.paper_id / "page-0002.png",
    ]

    manifest = PaperMetadata.model_validate_json(
        (tmp_path / "papers" / paper.paper_id / "metadata.json").read_text(encoding="utf-8")
    )
    assert manifest.status == PaperStatus.ready
    assert manifest.page_count == 2


def test_upload_marks_failed_and_returns_503_when_indexing_fails(tmp_path: Path) -> None:
    service = IngestionService(
        paths=StoragePaths(Settings(storage_root=tmp_path)),
        renderer=FakeRenderer(),
        indexing_service=FailingIndexer(),
    )
    upload = UploadFile(filename="paper.pdf", file=BytesIO(b"%PDF-1.7\n"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.accept_pdf_upload(file=upload, title=None))

    assert exc_info.value.status_code == 503
    [manifest_path] = list((tmp_path / "papers").glob("*/metadata.json"))
    manifest = PaperMetadata.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.status == PaperStatus.failed
    assert manifest.page_count == 2
