# Baseline Retrieval Metrics

## Methods And Evaluation Setup

| Field | Node 1 setup |
| --- | --- |
| Evaluation surface | Current FastAPI `POST /retrieval/search` route |
| Corpus mode | Synthetic smoke corpus because no real local PDFs are present under `storage/papers/` |
| Corpus size | 4 synthetic papers, 12 synthetic pages |
| Question set | 12 golden questions, including 3 refusal/negative cases (25.0%) |
| Scope fields | Fixture rows include `paper_ids`, optional `library_id`, `group_id`, and provenance |
| Retrieval path | `TestClient` plus dependency overrides; synthetic query embeddings; current `VectorStore` page upsert/search interface; in-memory Qdrant-compatible client |
| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness |
| Citation grain | Page-level `(paper_id, page_number)` correctness only |

## First Baseline Row

| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Boundary |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| node1-baseline | synthetic smoke corpus | 77.8% | 100.0% | 100.0% | 100.0% | 33.3% | Not a real-PDF, real-VisRAG, or real-local-corpus benchmark |

## Limitations

- No real local PDF corpus was present under `storage/papers/`, so Node 1 is not a real-PDF or real-local-corpus benchmark.
- Synthetic page captions stand in for rendered page evidence; this is not a real-VisRAG benchmark and real VisRAG model quality is not measured.
- Refusal correctness is retrieval-level no-evidence behavior, not generated answer refusal.
- The current raw retrieval route can return low-similarity pages for scoped hard negatives when no score threshold is used; later nodes should add calibrated evidence sufficiency gates before making answer-level claims.
