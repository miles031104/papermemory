from pathlib import Path

from app.core.config import Settings


class StoragePaths:
    """Centralizes local-first storage paths so services do not hard-code folders."""

    def __init__(self, settings: Settings) -> None:
        self.root = settings.storage_root

    @property
    def papers_dir(self) -> Path:
        return self.root / "papers"

    @property
    def uploads_dir(self) -> Path:
        return self.root / "uploads"

    @property
    def rendered_pages_dir(self) -> Path:
        return self.root / "rendered_pages"

    @property
    def indexes_dir(self) -> Path:
        return self.root / "indexes"

    @property
    def workspace_dir(self) -> Path:
        return self.root / "workspace"

    def ensure_all(self) -> None:
        for path in (
            self.root,
            self.papers_dir,
            self.uploads_dir,
            self.rendered_pages_dir,
            self.indexes_dir,
            self.workspace_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def paper_dir(self, paper_id: str) -> Path:
        return self.papers_dir / paper_id

    def paper_pdf_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "source.pdf"

    def paper_metadata_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "metadata.json"

    def page_images_dir(self, paper_id: str) -> Path:
        return self.rendered_pages_dir / paper_id

    def page_image_path(self, paper_id: str, page_number: int) -> Path:
        return self.page_images_dir(paper_id) / f"page-{page_number:04d}.png"
