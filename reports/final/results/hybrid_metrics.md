# Hybrid Retrieval Metrics

## Methods And Evaluation Setup

| Field | Node 5 setup |
| --- | --- |
| Evaluation surface | Direct `HybridRetrievalService` over synthetic fixtures |
| Corpus mode | Synthetic fixture baseline aligned to the existing golden paper/page IDs |
| Corpus size | 4 synthetic papers, 12 synthetic pages |
| Question set | 12 golden questions, including 3 refusal/negative cases (25.0%) |
| Retrieval path | Synthetic VisRAG vector store plus synthetic Node 3 `TextManifest` objects; page-canonical RRF fusion with `k=60` |
| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness, source coverage counts |
| Citation grain | Page-level `(paper_id, page_number)` correctness only |

## Hybrid Baseline Row

| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Both-trace units | Boundary |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| hybrid-baseline | synthetic hybrid fixture baseline | 77.8% | 100.0% | 100.0% | 100.0% | 33.3% | 27 | Not a real-PDF, real-corpus, or real-corpus improvement benchmark |

## Source Coverage

| Coverage type | Unit count |
| --- | ---: |
| Units with visual traces | 37 |
| Units with BM25 traces | 27 |
| Units with both visual and BM25 traces | 27 |
| Visual-only units | 10 |
| Text-only units | 0 |

## Interpretation

- Node 5 proves the additive page-canonical fusion path and provenance contract on fixtures.
- Overlapping pages collapse into one `hybrid_page` evidence unit with both source traces.
- The row is report/demo evidence for the retrieval contract only; it is not a real local corpus quality result.

## Limitations

- Synthetic captions and text manifests do not measure real PyMuPDF extraction or VisRAG embedding quality.
- Refusal correctness is retrieval-level no-hit behavior; answer-level abstention remains Node 6/7 work.
- No chat, UI, or multi-pass orchestration behavior is included in this node.
