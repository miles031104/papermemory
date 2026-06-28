from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.services.page_text_extractor import PageTextEntry, TextManifest


TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[._:/-][A-Za-z0-9]+)*")
CAMEL_CASE_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+")
COMPOUND_SPLIT_RE = re.compile(r"[._:/-]+")
SNIPPET_CHARS = 240
STOPWORDS = {
    "a",
    "about",
    "according",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "corpus",
    "describe",
    "describes",
    "does",
    "evidence",
    "for",
    "from",
    "gives",
    "help",
    "in",
    "instead",
    "is",
    "it",
    "no",
    "of",
    "on",
    "or",
    "page",
    "pages",
    "paper",
    "papers",
    "say",
    "selected",
    "should",
    "support",
    "supports",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
}


class TextSearchHit(BaseModel):
    paper_id: str
    page_number: int
    score: float
    rank: int = Field(ge=1)
    snippet: str | None
    matched_terms: list[str]
    quality_label: str | None = None
    ocr_needed: bool | None = None
    char_count: int | None = None
    word_count: int | None = None
    source: Literal["bm25_text"] = "bm25_text"


@dataclass(frozen=True)
class _TextDocument:
    paper_id: str
    page_number: int
    text: str
    snippets: tuple[str, ...]
    term_counts: Counter[str]
    length: int
    quality_label: str | None = None
    ocr_needed: bool | None = None
    char_count: int | None = None
    word_count: int | None = None


class TextRetriever:
    """Deterministic BM25 retriever over page-level text manifests."""

    def __init__(
        self,
        documents: Sequence[_TextDocument],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self.average_document_length = (
            sum(document.length for document in self.documents) / len(self.documents)
            if self.documents
            else 0.0
        )
        self.idf = self._build_idf(self.documents)

    @classmethod
    def from_manifests(cls, manifests: Sequence[TextManifest]) -> "TextRetriever":
        documents: list[_TextDocument] = []
        for manifest in manifests:
            for page in manifest.pages:
                document = _document_from_page(page)
                if document is not None:
                    documents.append(document)
        return cls(documents)

    def search(
        self,
        query: str,
        *,
        paper_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[TextSearchHit]:
        query_terms = _ordered_unique(tokenize(query))
        if not query_terms or top_k <= 0:
            return []
        if paper_ids is not None and not paper_ids:
            return []

        allowed_papers = set(paper_ids) if paper_ids is not None else None
        scored_hits: list[tuple[float, _TextDocument, list[str]]] = []
        for document in self.documents:
            if allowed_papers is not None and document.paper_id not in allowed_papers:
                continue

            score, matched_terms = self._score_document(document, query_terms)
            if score <= 0.0:
                continue
            scored_hits.append((score, document, matched_terms))

        scored_hits.sort(key=lambda item: (-item[0], item[1].paper_id, item[1].page_number))
        hits: list[TextSearchHit] = []
        for rank, (score, document, matched_terms) in enumerate(scored_hits[:top_k], start=1):
            hits.append(
                TextSearchHit(
                    paper_id=document.paper_id,
                    page_number=document.page_number,
                    score=score,
                    rank=rank,
                    snippet=_best_snippet(document, matched_terms),
                    matched_terms=matched_terms,
                    quality_label=document.quality_label,
                    ocr_needed=document.ocr_needed,
                    char_count=document.char_count,
                    word_count=document.word_count,
                )
            )
        return hits

    @staticmethod
    def _build_idf(documents: Sequence[_TextDocument]) -> dict[str, float]:
        document_count = len(documents)
        document_frequency: Counter[str] = Counter()
        for document in documents:
            document_frequency.update(document.term_counts.keys())

        return {
            term: math.log(1.0 + (document_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def _score_document(
        self,
        document: _TextDocument,
        query_terms: Sequence[str],
    ) -> tuple[float, list[str]]:
        if self.average_document_length <= 0.0 or document.length <= 0:
            return 0.0, []

        score = 0.0
        matched_terms: list[str] = []
        length_norm = 1.0 - self.b + self.b * (
            document.length / self.average_document_length
        )
        for term in query_terms:
            term_frequency = document.term_counts.get(term, 0)
            if term_frequency <= 0:
                continue
            numerator = term_frequency * (self.k1 + 1.0)
            denominator = term_frequency + self.k1 * length_norm
            score += self.idf.get(term, 0.0) * (numerator / denominator)
            matched_terms.append(term)
        return score, matched_terms


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []

    tokens: list[str] = []
    for match in TOKEN_RE.finditer(text):
        raw_token = match.group(0)
        token = raw_token.lower()
        _append_token(tokens, token)
        if any(separator in token for separator in ".:/-_"):
            for part in COMPOUND_SPLIT_RE.split(token):
                _append_token(tokens, part)
        if re.search(r"[a-z][A-Z]", raw_token):
            for part in CAMEL_CASE_RE.findall(raw_token):
                _append_token(tokens, part.lower())
    return tokens


def _document_from_page(page: PageTextEntry) -> _TextDocument | None:
    if not page.quality.has_text:
        return None

    text = (page.text or "").strip()
    block_texts = tuple(block.text.strip() for block in page.blocks if block.text.strip())
    if not text and block_texts:
        text = "\n".join(block_texts)
    if not text:
        return None

    snippets = block_texts or (text,)
    term_counts = Counter(tokenize(text))
    if not term_counts:
        return None

    return _TextDocument(
        paper_id=page.paper_id,
        page_number=page.page_number,
        text=text,
        snippets=snippets,
        term_counts=term_counts,
        length=sum(term_counts.values()),
        quality_label=page.quality.quality_label,
        ocr_needed=page.quality.ocr_needed,
        char_count=page.quality.char_count,
        word_count=page.quality.word_count,
    )


def _best_snippet(document: _TextDocument, matched_terms: Sequence[str]) -> str | None:
    if not matched_terms:
        return None

    best_text = document.text
    best_score = -1
    for snippet_text in document.snippets:
        snippet_terms = set(tokenize(snippet_text))
        snippet_score = sum(1 for term in matched_terms if term in snippet_terms)
        if snippet_score > best_score:
            best_score = snippet_score
            best_text = snippet_text

    return _shorten_snippet(best_text, matched_terms)


def _shorten_snippet(text: str, matched_terms: Sequence[str]) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= SNIPPET_CHARS:
        return normalized

    lowered = normalized.lower()
    first_match = min(
        (index for term in matched_terms if (index := lowered.find(term)) >= 0),
        default=0,
    )
    half_window = SNIPPET_CHARS // 2
    start = max(0, first_match - half_window)
    end = min(len(normalized), start + SNIPPET_CHARS)
    start = max(0, end - SNIPPET_CHARS)
    snippet = normalized[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(normalized):
        snippet += "..."
    return snippet


def _ordered_unique(tokens: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique


def _append_token(tokens: list[str], token: str) -> None:
    if token and token not in STOPWORDS:
        tokens.append(token)
