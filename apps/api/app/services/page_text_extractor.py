from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.services.pdf_renderer import PdfRenderer


BBox = tuple[float, float, float, float]


class TextWord(BaseModel):
    text: str
    bbox: BBox
    block_number: int | None
    line_number: int | None
    word_number: int | None


class TextBlock(BaseModel):
    block_number: int
    text: str
    bbox: BBox
    word_count: int


class PageTextQuality(BaseModel):
    char_count: int
    word_count: int
    block_count: int
    has_text: bool
    ocr_needed: bool
    quality_label: Literal["good", "low_text", "empty"]


class PageTextEntry(BaseModel):
    paper_id: str
    page_number: int = Field(ge=1)
    width: float
    height: float
    text: str | None
    caption: str | None
    blocks: list[TextBlock]
    words: list[TextWord]
    quality: PageTextQuality


class TextManifest(BaseModel):
    schema_version: Literal["text_manifest.v0"] = "text_manifest.v0"
    paper_id: str
    page_count: int = Field(ge=0)
    pages: list[PageTextEntry]


class PageTextExtractor:
    """Extracts structured, page-aligned selectable text from a local PDF."""

    def __init__(self, max_caption_chars: int = PdfRenderer._MAX_CAPTION_CHARS) -> None:
        self.max_caption_chars = max_caption_chars

    def extract(self, pdf_path: Path, paper_id: str) -> TextManifest:
        import fitz

        pages: list[PageTextEntry] = []
        with fitz.open(pdf_path) as document:
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                raw_text = page.get_text("text").strip()
                words = self._extract_words(page)
                blocks = self._extract_blocks(page)
                quality = self._quality(raw_text=raw_text, words=words, blocks=blocks)
                text = raw_text or None

                pages.append(
                    PageTextEntry(
                        paper_id=paper_id,
                        page_number=page_index + 1,
                        width=float(page.rect.width),
                        height=float(page.rect.height),
                        text=text,
                        caption=text[: self.max_caption_chars] if text else None,
                        blocks=blocks,
                        words=words,
                        quality=quality,
                    )
                )

        return TextManifest(
            paper_id=paper_id,
            page_count=len(pages),
            pages=pages,
        )

    def _extract_blocks(self, page) -> list[TextBlock]:
        blocks: list[TextBlock] = []
        for fallback_number, block in enumerate(page.get_text("blocks")):
            if len(block) < 5:
                continue
            text = str(block[4]).strip()
            if not text:
                continue
            block_type = int(block[6]) if len(block) > 6 else 0
            if block_type != 0:
                continue
            block_number = int(block[5]) if len(block) > 5 else fallback_number
            blocks.append(
                TextBlock(
                    block_number=block_number,
                    text=text,
                    bbox=self._bbox(block),
                    word_count=len(text.split()),
                )
            )
        return blocks

    def _extract_words(self, page) -> list[TextWord]:
        words: list[TextWord] = []
        for word in page.get_text("words"):
            if len(word) < 5:
                continue
            text = str(word[4]).strip()
            if not text:
                continue
            words.append(
                TextWord(
                    text=text,
                    bbox=self._bbox(word),
                    block_number=int(word[5]) if len(word) > 5 else None,
                    line_number=int(word[6]) if len(word) > 6 else None,
                    word_number=int(word[7]) if len(word) > 7 else None,
                )
            )
        return words

    def _quality(
        self,
        raw_text: str,
        words: list[TextWord],
        blocks: list[TextBlock],
    ) -> PageTextQuality:
        char_count = len(raw_text)
        word_count = len(words) if words else len(raw_text.split())
        has_text = bool(raw_text)
        if not has_text:
            quality_label: Literal["good", "low_text", "empty"] = "empty"
        elif char_count < 20 or word_count < 3:
            quality_label = "low_text"
        else:
            quality_label = "good"

        return PageTextQuality(
            char_count=char_count,
            word_count=word_count,
            block_count=len(blocks),
            has_text=has_text,
            ocr_needed=quality_label != "good",
            quality_label=quality_label,
        )

    @staticmethod
    def _bbox(values) -> BBox:
        return (
            float(values[0]),
            float(values[1]),
            float(values[2]),
            float(values[3]),
        )
