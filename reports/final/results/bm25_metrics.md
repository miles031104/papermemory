# BM25 Text Retrieval Metrics

## Methods And Evaluation Setup

| Field | Node 4 setup |
| --- | --- |
| Evaluation surface | Direct `TextRetriever` over synthetic Node 3 `TextManifest` objects |
| Corpus mode | Synthetic text-manifest corpus aligned to the existing golden fixture paper/page IDs |
| Corpus size | 4 synthetic papers, 12 synthetic pages |
| Question set | 12 golden questions, including 3 refusal/negative cases (25.0%) |
| Retrieval path | Local deterministic BM25 only; no FastAPI route, VisRAG, Qdrant, chat, hybrid fusion, or RRF |
| BM25 parameters | `k1=1.5`, `b=0.75` |
| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness |
| Citation grain | Page-level `(paper_id, page_number)` correctness only |

## BM25 Baseline Row

| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Boundary |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| bm25-baseline | synthetic BM25-only text manifest | 88.9% | 100.0% | 100.0% | 100.0% | 100.0% | Not a real-PDF, real-corpus, hybrid, RRF, or VisRAG benchmark |

## Interpretation

- BM25 provides an explainable exact-term page retriever for text-bearing pages from Node 3 manifests.
- BM25 is useful for method names, dataset names, abbreviations, and citation-like tokens when selectable text exists.
- BM25 does not replace the current visual `/retrieval/search` route in Node 4.
- This row is a synthetic measurement artifact for report/demo progress, not a claim of real local corpus quality.

## Limitations

- The synthetic text corpus is title/caption based and does not measure real PyMuPDF extraction quality.
- Refusal correctness is retrieval-level no-hit behavior; answer-level abstention is still later orchestration work.
- Hybrid page-canonical fusion is explicitly deferred to Node 5.
