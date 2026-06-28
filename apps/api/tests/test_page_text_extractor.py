from pathlib import Path

from app.services.page_text_extractor import PageTextExtractor
from app.services.pdf_renderer import PdfRenderer


def _write_pdf(
    path: Path,
    page_texts: list[str | None],
    width: int = 320,
    height: int = 240,
    fontsize: int = 12,
) -> None:
    import fitz

    document = fitz.open()
    for text in page_texts:
        page = document.new_page(width=width, height=height)
        if text:
            page.insert_textbox(
                fitz.Rect(36, 36, width - 36, height - 36),
                text,
                fontsize=fontsize,
            )
    document.save(path)
    document.close()


def test_extracts_structured_text_blocks_words_dimensions_and_quality(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    text = (
        "PaperMemory text manifest stores structured PyMuPDF words and blocks "
        "for retrieval planning."
    )
    _write_pdf(pdf_path, [text])

    manifest = PageTextExtractor().extract(pdf_path=pdf_path, paper_id="paper-1")

    assert manifest.schema_version == "text_manifest.v0"
    assert manifest.paper_id == "paper-1"
    assert manifest.page_count == 1

    page = manifest.pages[0]
    assert page.paper_id == "paper-1"
    assert page.page_number == 1
    assert page.width == 320
    assert page.height == 240
    assert page.text is not None
    assert "PaperMemory text manifest" in page.text
    assert page.caption == page.text[: PdfRenderer._MAX_CAPTION_CHARS]
    assert page.quality.quality_label == "good"
    assert page.quality.has_text is True
    assert page.quality.ocr_needed is False
    assert page.quality.char_count == len(page.text)
    assert page.quality.word_count >= 10
    assert page.quality.block_count >= 1

    assert page.blocks
    assert page.blocks[0].block_number >= 0
    assert page.blocks[0].word_count >= 1
    assert len(page.blocks[0].bbox) == 4
    assert all(isinstance(value, float) for value in page.blocks[0].bbox)

    assert page.words
    assert any(word.text == "PaperMemory" for word in page.words)
    assert len(page.words[0].bbox) == 4
    assert page.words[0].block_number is not None
    assert page.words[0].line_number is not None
    assert page.words[0].word_number is not None


def test_marks_empty_and_low_text_pages_as_ocr_needed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "weak.pdf"
    _write_pdf(pdf_path, [None, "Hi"])

    manifest = PageTextExtractor().extract(pdf_path=pdf_path, paper_id="weak-paper")

    empty_page = manifest.pages[0]
    assert empty_page.page_number == 1
    assert empty_page.text is None
    assert empty_page.caption is None
    assert empty_page.blocks == []
    assert empty_page.words == []
    assert empty_page.quality.quality_label == "empty"
    assert empty_page.quality.has_text is False
    assert empty_page.quality.ocr_needed is True

    low_text_page = manifest.pages[1]
    assert low_text_page.page_number == 2
    assert low_text_page.text == "Hi"
    assert low_text_page.caption == "Hi"
    assert low_text_page.quality.quality_label == "low_text"
    assert low_text_page.quality.has_text is True
    assert low_text_page.quality.ocr_needed is True


def test_caption_is_bounded_to_pdf_renderer_limit(tmp_path: Path) -> None:
    pdf_path = tmp_path / "long.pdf"
    long_text = " ".join(f"token{i:04d}" for i in range(500))
    _write_pdf(pdf_path, [long_text], width=1200, height=2400, fontsize=8)

    page = PageTextExtractor().extract(pdf_path=pdf_path, paper_id="long-paper").pages[0]

    assert page.text is not None
    assert len(page.caption or "") == PdfRenderer._MAX_CAPTION_CHARS
    assert page.caption == page.text[: PdfRenderer._MAX_CAPTION_CHARS]
