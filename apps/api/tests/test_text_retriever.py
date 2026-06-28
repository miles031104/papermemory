from app.services.page_text_extractor import (
    PageTextEntry,
    PageTextQuality,
    TextBlock,
    TextManifest,
)
from app.services.text_retriever import TextRetriever


def _quality(text: str | None, *, has_text: bool = True) -> PageTextQuality:
    words = text.split() if text else []
    return PageTextQuality(
        char_count=len(text or ""),
        word_count=len(words),
        block_count=1 if text else 0,
        has_text=has_text,
        ocr_needed=not has_text,
        quality_label="good" if has_text and text else "empty",
    )


def _page(
    paper_id: str,
    page_number: int,
    text: str | None,
    *,
    has_text: bool = True,
    blocks: list[str] | None = None,
) -> PageTextEntry:
    block_texts = blocks if blocks is not None else ([text] if text else [])
    return PageTextEntry(
        paper_id=paper_id,
        page_number=page_number,
        width=320.0,
        height=240.0,
        text=text,
        caption=text[:80] if text else None,
        blocks=[
            TextBlock(
                block_number=index,
                text=block_text,
                bbox=(1.0, 2.0, 3.0, 4.0),
                word_count=len(block_text.split()),
            )
            for index, block_text in enumerate(block_texts)
        ],
        words=[],
        quality=_quality(text, has_text=has_text),
    )


def _manifest(paper_id: str, pages: list[PageTextEntry]) -> TextManifest:
    return TextManifest(paper_id=paper_id, page_count=len(pages), pages=pages)


def test_search_ranks_method_dataset_abbreviation_and_citation_tokens() -> None:
    retriever = TextRetriever.from_manifests(
        [
            _manifest(
                "paper-alpha",
                [
                    _page(
                        "paper-alpha",
                        1,
                        (
                            "The ViT-B/16 retrieval method uses LoRA adapters on "
                            "MS-COCO and cites [Smith2020] for the exact baseline."
                        ),
                    ),
                    _page(
                        "paper-alpha",
                        2,
                        "A general discussion of local privacy and page evidence.",
                    ),
                ],
            )
        ]
    )

    hits = retriever.search(
        "Does ViT-B/16 use LoRA on MS-COCO according to [Smith2020]?",
        paper_ids=["paper-alpha"],
        top_k=3,
    )

    assert len(hits) == 1
    hit = hits[0]
    assert hit.paper_id == "paper-alpha"
    assert hit.page_number == 1
    assert hit.rank == 1
    assert hit.score > 0
    assert hit.source == "bm25_text"
    assert hit.snippet is not None
    assert "ViT-B/16" in hit.snippet
    assert "MS-COCO" in hit.snippet
    assert {"vit-b/16", "lora", "ms-coco", "smith2020"}.issubset(hit.matched_terms)


def test_scope_filtering_and_empty_scope_prevent_paper_leaks() -> None:
    retriever = TextRetriever.from_manifests(
        [
            _manifest(
                "paper-alpha",
                [_page("paper-alpha", 1, "BM25 baseline for PaperMemory.")],
            ),
            _manifest(
                "paper-beta",
                [_page("paper-beta", 1, "BM25 baseline for a separate paper.")],
            ),
        ]
    )

    assert retriever.search("BM25", paper_ids=[]) == []

    scoped_hits = retriever.search("BM25 baseline", paper_ids=["paper-beta"], top_k=5)

    assert [hit.paper_id for hit in scoped_hits] == ["paper-beta"]
    assert [hit.rank for hit in scoped_hits] == [1]


def test_search_skips_pages_without_selectable_text_and_blank_queries() -> None:
    retriever = TextRetriever.from_manifests(
        [
            _manifest(
                "paper-alpha",
                [
                    _page(
                        "paper-alpha",
                        1,
                        "Hidden MS-COCO OCR text should not be indexed.",
                        has_text=False,
                    ),
                    _page("paper-alpha", 2, None, has_text=False),
                    _page("paper-alpha", 3, "Visible BM25 text is indexable."),
                ],
            )
        ]
    )

    assert retriever.search("MS-COCO", paper_ids=["paper-alpha"]) == []
    assert retriever.search("   ", paper_ids=["paper-alpha"]) == []


def test_snippet_uses_matching_block_without_inventing_text() -> None:
    expected_block = "The second block explains BM25 scoring with RRF deferred."
    retriever = TextRetriever.from_manifests(
        [
            _manifest(
                "paper-alpha",
                [
                    _page(
                        "paper-alpha",
                        1,
                        "Overview block. " + expected_block,
                        blocks=["Overview block.", expected_block],
                    )
                ],
            )
        ]
    )

    hit = retriever.search("BM25 RRF", paper_ids=["paper-alpha"])[0]

    assert hit.snippet == expected_block
    assert hit.matched_terms == ["bm25", "rrf"]


def test_common_question_words_do_not_create_hard_negative_hits() -> None:
    retriever = TextRetriever.from_manifests(
        [
            _manifest(
                "paper-alpha",
                [
                    _page(
                        "paper-alpha",
                        1,
                        "Page citation correctness checks expected paper pages.",
                    )
                ],
            )
        ]
    )

    hits = retriever.search(
        "Which page gives exact p-values for a cancer clinical trial?",
        paper_ids=["paper-alpha"],
    )

    assert hits == []
