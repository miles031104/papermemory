from pathlib import Path


class PdfRenderer:
    """Renders local PDFs into page images, matching the first VisRAG ingestion step."""

    # Maximum characters kept per page. Long pages are truncated so captions
    # don't bloat the LLM context window.
    _MAX_CAPTION_CHARS = 2000

    def __init__(self, zoom: float = 2.0, max_pages: int = 200) -> None:
        self.zoom = zoom
        self.max_pages = max_pages

    def render_pages(self, pdf_path: Path, output_dir: Path) -> list[Path]:
        import fitz

        output_dir.mkdir(parents=True, exist_ok=True)
        rendered_paths: list[Path] = []

        with fitz.open(pdf_path) as document:
            if document.page_count > self.max_pages:
                raise ValueError(
                    f"PDF has {document.page_count} pages, which exceeds the configured limit of {self.max_pages}."
                )
            matrix = fitz.Matrix(self.zoom, self.zoom)
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_path = output_dir / f"page-{page_index + 1:04d}.png"
                pixmap.save(image_path)
                rendered_paths.append(image_path)

        return rendered_paths

    def extract_page_texts(self, pdf_path: Path) -> list[str | None]:
        """Extract plain text from each PDF page using PyMuPDF.

        Returns one entry per page (None when a page has no selectable text,
        e.g. a scanned image page).  Texts are truncated to ``_MAX_CAPTION_CHARS``
        to keep vector store payloads and LLM context windows manageable.
        """
        import fitz

        texts: list[str | None] = []
        with fitz.open(pdf_path) as document:
            for page_index in range(document.page_count):
                raw = document.load_page(page_index).get_text("text").strip()
                if raw:
                    texts.append(raw[: self._MAX_CAPTION_CHARS])
                else:
                    texts.append(None)
        return texts
