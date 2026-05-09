from datetime import UTC, datetime
from pathlib import Path
import shutil
from typing import Protocol, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.paths import StoragePaths
from app.schemas.papers import PaperMetadata, PaperStatus
from app.services.pdf_renderer import PdfRenderer


class PageRenderer(Protocol):
    def render_pages(self, pdf_path: Path, output_dir: Path) -> list[Path]:
        ...


class PageIndexer(Protocol):
    async def index_pages(self, paper_id: str, page_paths: Sequence[Path]) -> None:
        ...


class IngestionService:
    """Accepts local PDFs and owns the future page-rendering/indexing workflow."""

    def __init__(
        self,
        paths: StoragePaths,
        renderer: PageRenderer | None = None,
        indexing_service: PageIndexer | None = None,
        max_upload_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        self.paths = paths
        self.renderer = renderer or PdfRenderer()
        self.indexing_service = indexing_service
        self.max_upload_bytes = max_upload_bytes
        self.paths.ensure_all()

    async def accept_pdf_upload(self, file: UploadFile, title: str | None = None) -> PaperMetadata:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

        paper_id = uuid4().hex
        paper_dir = self.paths.paper_dir(paper_id)
        paper_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = self.paths.paper_pdf_path(paper_id)

        created_at = datetime.now(UTC)
        metadata = PaperMetadata(
            paper_id=paper_id,
            title=title,
            filename=file.filename,
            status=PaperStatus.processing,
            page_count=None,
            created_at=created_at,
        )
        self._write_metadata(metadata)

        try:
            await self._write_upload(file=file, destination=pdf_path)
        except HTTPException:
            failed_metadata = metadata.model_copy(update={"status": PaperStatus.failed})
            self._write_metadata(failed_metadata)
            self._cleanup_paper_files(paper_id)
            raise

        try:
            rendered_pages = await self.render_pdf_pages(paper_id=paper_id)
        except Exception as exc:
            failed_metadata = metadata.model_copy(update={"status": PaperStatus.failed})
            self._write_metadata(failed_metadata)
            raise HTTPException(status_code=422, detail=f"Failed to render PDF pages: {exc}") from exc

        indexing_metadata = metadata.model_copy(
            update={
                "status": PaperStatus.indexing,
                "page_count": len(rendered_pages),
            }
        )
        self._write_metadata(indexing_metadata)

        try:
            if self.indexing_service is not None:
                await self.indexing_service.index_pages(paper_id=paper_id, page_paths=rendered_pages)
        except Exception as exc:
            failed_metadata = indexing_metadata.model_copy(update={"status": PaperStatus.failed})
            self._write_metadata(failed_metadata)
            raise HTTPException(status_code=503, detail=f"Failed to index PDF pages: {exc}") from exc

        ready_metadata = indexing_metadata.model_copy(update={"status": PaperStatus.ready})
        self._write_metadata(ready_metadata)
        return ready_metadata

    def list_papers(self) -> list[PaperMetadata]:
        papers: list[PaperMetadata] = []
        for metadata_path in sorted(self.paths.papers_dir.glob("*/metadata.json")):
            papers.append(PaperMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8")))
        return papers

    def get_paper(self, paper_id: str) -> PaperMetadata:
        metadata_path = self.paths.paper_metadata_path(paper_id)
        if not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Paper not found.")
        return PaperMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))

    async def render_pdf_pages(self, paper_id: str) -> list[Path]:
        pdf_path = self.paths.paper_pdf_path(paper_id)
        output_dir = self.paths.page_images_dir(paper_id)
        return self.renderer.render_pages(pdf_path=pdf_path, output_dir=output_dir)

    async def _write_upload(self, file: UploadFile, destination: Path) -> None:
        total_bytes = 0
        saw_first_chunk = False
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                if not saw_first_chunk:
                    saw_first_chunk = True
                    if not chunk.startswith(b"%PDF"):
                        raise HTTPException(status_code=415, detail="Uploaded file does not look like a PDF.")
                total_bytes += len(chunk)
                if total_bytes > self.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="PDF exceeds the configured upload size limit.")
                output.write(chunk)
        if not saw_first_chunk:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    def _write_metadata(self, metadata: PaperMetadata) -> None:
        metadata_path = self.paths.paper_metadata_path(metadata.paper_id)
        metadata_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

    def _cleanup_paper_files(self, paper_id: str) -> None:
        shutil.rmtree(self.paths.paper_dir(paper_id), ignore_errors=True)
        shutil.rmtree(self.paths.page_images_dir(paper_id), ignore_errors=True)
