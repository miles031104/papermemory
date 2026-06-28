import asyncio
from datetime import UTC, datetime
from pathlib import Path
import shutil
from typing import Protocol, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.paths import StoragePaths
from app.schemas.papers import PaperMetadata, PaperStatus, is_safe_paper_id
from app.services.page_text_extractor import PageTextExtractor, TextManifest
from app.services.pdf_renderer import PdfRenderer
from app.services.text_manifest_store import TextManifestStore


class PageRenderer(Protocol):
    def render_pages(self, pdf_path: Path, output_dir: Path) -> list[Path]:
        ...


class PageIndexer(Protocol):
    async def index_pages(
        self,
        paper_id: str,
        page_paths: Sequence[Path],
        captions: Sequence[str | None] | None = None,
    ) -> None:
        ...


class IngestionService:
    """Accepts local PDFs and owns the future page-rendering/indexing workflow."""

    def __init__(
        self,
        paths: StoragePaths,
        renderer: PageRenderer | None = None,
        indexing_service: PageIndexer | None = None,
        text_extractor: PageTextExtractor | None = None,
        text_manifest_store: TextManifestStore | None = None,
        max_upload_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        self.paths = paths
        self.renderer = renderer or PdfRenderer()
        self.indexing_service = indexing_service
        self.text_extractor = text_extractor or PageTextExtractor()
        self.text_manifest_store = text_manifest_store or TextManifestStore(paths)
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

        text_manifest = await self._extract_text_manifest(paper_id=paper_id)
        page_texts = self._captions_for_indexing(
            manifest=text_manifest,
            rendered_page_count=len(rendered_pages),
        )

        indexing_metadata = metadata.model_copy(
            update={
                "status": PaperStatus.indexing,
                "page_count": len(rendered_pages),
            }
        )
        self._write_metadata(indexing_metadata)

        try:
            if self.indexing_service is not None:
                await self.indexing_service.index_pages(
                    paper_id=paper_id,
                    page_paths=rendered_pages,
                    captions=page_texts,
                )
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

    def delete_paper(self, paper_id: str) -> None:
        if not is_safe_paper_id(paper_id):
            raise HTTPException(status_code=400, detail="Invalid paper id.")
        self.get_paper(paper_id)
        self._cleanup_paper_files(paper_id)

    def get_page_image_path(self, paper_id: str, page_number: int) -> Path:
        if not is_safe_paper_id(paper_id):
            raise HTTPException(status_code=400, detail="Invalid paper id.")
        if page_number < 1:
            raise HTTPException(status_code=400, detail="Page number must be at least 1.")

        self.get_paper(paper_id)

        image_path = self.paths.page_image_path(paper_id=paper_id, page_number=page_number).resolve()
        rendered_root = self.paths.rendered_pages_dir.resolve()
        try:
            image_path.relative_to(rendered_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid page image path.") from exc

        if not image_path.is_file():
            raise HTTPException(status_code=404, detail="Page image not found.")
        return image_path

    async def render_pdf_pages(self, paper_id: str) -> list[Path]:
        pdf_path = self.paths.paper_pdf_path(paper_id)
        output_dir = self.paths.page_images_dir(paper_id)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.renderer.render_pages, pdf_path, output_dir
        )

    async def _extract_text_manifest(self, paper_id: str) -> TextManifest | None:
        """Extract and persist page text; returns None on extraction/storage errors."""
        pdf_path = self.paths.paper_pdf_path(paper_id)
        loop = asyncio.get_event_loop()
        try:
            manifest = await loop.run_in_executor(
                None,
                self.text_extractor.extract,
                pdf_path,
                paper_id,
            )
            await loop.run_in_executor(None, self.text_manifest_store.save, manifest)
            return manifest
        except Exception:
            return None

    @staticmethod
    def _captions_for_indexing(
        manifest: TextManifest | None,
        rendered_page_count: int,
    ) -> list[str | None]:
        if manifest is None:
            return []
        if manifest.page_count != rendered_page_count:
            return []
        return [page.caption for page in manifest.pages]

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
        try:
            self.text_manifest_store.path_for(paper_id).unlink(missing_ok=True)
        except ValueError:
            pass
