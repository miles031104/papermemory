from app.core.paths import StoragePaths
from app.schemas.papers import is_safe_paper_id
from app.schemas.retrieval import PageEvidence


class PageImageResolver:
    """Resolves page evidence to storage-owned rendered page image paths."""

    def __init__(self, paths: StoragePaths) -> None:
        self.paths = paths

    def resolve_evidence_image_path(self, evidence: PageEvidence) -> str | None:
        if not is_safe_paper_id(evidence.paper_id) or evidence.page_number < 1:
            return None

        image_path = self.paths.page_image_path(
            paper_id=evidence.paper_id,
            page_number=evidence.page_number,
        ).resolve()
        rendered_root = self.paths.rendered_pages_dir.resolve()

        try:
            image_path.relative_to(rendered_root)
        except ValueError:
            return None

        if not image_path.is_file():
            return None
        return str(image_path)
