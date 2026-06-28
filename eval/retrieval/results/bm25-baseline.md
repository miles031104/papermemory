# Node 4 BM25 Text Baseline

Mode: synthetic BM25-only text-manifest corpus.

This run builds synthetic `TextManifest` objects aligned to the Node 1 golden fixture paper/page IDs and calls `TextRetriever` directly. It does not call VisRAG, Qdrant, `/retrieval/search`, chat, hybrid fusion, or RRF.

## Metrics

| Metric | Value |
| --- | ---: |
| Questions | 12 |
| Negative/refusal share | 25.0% |
| Recall@1 | 88.9% |
| Recall@3 | 100.0% |
| Recall@5 | 100.0% |
| Citation-page correctness | 100.0% |
| Refusal correctness | 100.0% |

## Per-Question Results

| ID | Type | Expected | BM25 top pages | R@5 | Cite pages correct | Refusal correct |
| --- | --- | --- | --- | ---: | --- | --- |
| gq-001 | single_paper_fact | demo-visrag-core:1 | demo-visrag-core:1, demo-visrag-core:3, demo-visrag-core:2 | 100.0% | yes | n/a |
| gq-002 | single_paper_fact | demo-visrag-core:2 | demo-visrag-core:2, demo-visrag-core:1, demo-visrag-core:3 | 100.0% | yes | n/a |
| gq-003 | single_paper_fact | demo-bm25-text:1 | demo-bm25-text:1, demo-bm25-text:2 | 100.0% | yes | n/a |
| gq-004 | single_paper_fact | demo-bm25-text:2 | demo-bm25-text:2, demo-bm25-text:1, demo-bm25-text:3 | 100.0% | yes | n/a |
| gq-005 | single_paper_fact | demo-bm25-text:3 | demo-bm25-text:3, demo-bm25-text:2, demo-bm25-text:1 | 100.0% | yes | n/a |
| gq-006 | multi_page_within_paper | demo-agentic-rag:1, demo-agentic-rag:2 | demo-agentic-rag:2, demo-agentic-rag:1, demo-agentic-rag:3 | 100.0% | yes | n/a |
| gq-007 | multi_paper_comparison | demo-bm25-text:1, demo-visrag-core:1 | demo-visrag-core:1, demo-bm25-text:1, demo-bm25-text:2, demo-visrag-core:3, demo-visrag-core:2 | 100.0% | yes | n/a |
| gq-008 | metric_definition | demo-risk-eval:2 | demo-risk-eval:2, demo-risk-eval:1, demo-risk-eval:3 | 100.0% | yes | n/a |
| gq-009 | single_paper_fact | demo-risk-eval:3 | demo-risk-eval:3, demo-risk-eval:2 | 100.0% | yes | n/a |
| gq-010 | refusal_missing_evidence | n/a | none | n/a | n/a | yes |
| gq-011 | refusal_empty_scope | n/a | none | n/a | n/a | yes |
| gq-012 | refusal_missing_evidence | n/a | none | n/a | n/a | yes |

## Boundary

- BM25 scores are lexical text scores from `TextRetriever`; they are not visual scores.
- Synthetic text pages are derived from the existing golden fixture captions and titles.
- Refusal correctness means BM25 returned no page hits for a refusal row. It is not answer-level refusal generation.
- Node 5 remains responsible for page-canonical hybrid/RRF fusion.
