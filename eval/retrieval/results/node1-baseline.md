# Node 1 Retrieval Baseline

Mode: synthetic smoke corpus.

This run exercises the current FastAPI `POST /retrieval/search` route through `TestClient` dependency overrides. It seeds a deterministic page-level corpus through the current `VectorStore.upsert_page` and `VectorStore.search_pages` interfaces using an in-memory Qdrant-compatible client. This is not a real-PDF, real-VisRAG, or real-local-corpus benchmark.

## Metrics

| Metric | Value |
| --- | ---: |
| Questions | 12 |
| Negative/refusal share | 25.0% |
| Recall@1 | 77.8% |
| Recall@3 | 100.0% |
| Recall@5 | 100.0% |
| Citation-page correctness | 100.0% |
| Refusal correctness | 33.3% |

## Per-Question Results

| ID | Type | Expected | Top evidence | R@5 | Cite pages correct | Refusal correct |
| --- | --- | --- | --- | ---: | --- | --- |
| gq-001 | single_paper_fact | demo-visrag-core:1 | demo-visrag-core:1, demo-visrag-core:3, demo-visrag-core:2 | 100.0% | yes | n/a |
| gq-002 | single_paper_fact | demo-visrag-core:2 | demo-visrag-core:2, demo-visrag-core:1, demo-visrag-core:3 | 100.0% | yes | n/a |
| gq-003 | single_paper_fact | demo-bm25-text:1 | demo-bm25-text:1, demo-bm25-text:2, demo-bm25-text:3 | 100.0% | yes | n/a |
| gq-004 | single_paper_fact | demo-bm25-text:2 | demo-bm25-text:2, demo-bm25-text:1, demo-bm25-text:3 | 100.0% | yes | n/a |
| gq-005 | single_paper_fact | demo-bm25-text:3 | demo-bm25-text:2, demo-bm25-text:3, demo-bm25-text:1 | 100.0% | yes | n/a |
| gq-006 | multi_page_within_paper | demo-agentic-rag:1, demo-agentic-rag:2 | demo-agentic-rag:1, demo-agentic-rag:3, demo-agentic-rag:2 | 100.0% | yes | n/a |
| gq-007 | multi_paper_comparison | demo-bm25-text:1, demo-visrag-core:1 | demo-bm25-text:1, demo-visrag-core:1, demo-visrag-core:3, demo-bm25-text:2, demo-visrag-core:2 | 100.0% | yes | n/a |
| gq-008 | metric_definition | demo-risk-eval:2 | demo-risk-eval:2, demo-risk-eval:1, demo-risk-eval:3 | 100.0% | yes | n/a |
| gq-009 | single_paper_fact | demo-risk-eval:3 | demo-risk-eval:3, demo-risk-eval:2, demo-risk-eval:1 | 100.0% | yes | n/a |
| gq-010 | refusal_missing_evidence | n/a | demo-agentic-rag:2, demo-agentic-rag:3, demo-risk-eval:1, demo-risk-eval:3, demo-risk-eval:2 | n/a | n/a | no |
| gq-011 | refusal_empty_scope | n/a | none | n/a | n/a | yes |
| gq-012 | refusal_missing_evidence | n/a | demo-risk-eval:2, demo-risk-eval:1, demo-risk-eval:3 | n/a | n/a | no |

## Boundary

- Synthetic paper IDs are stable aliases such as `demo-visrag-core` and `demo-bm25-text`.
- `library_id` and `group_id` are recorded in the fixture to match the current Paper Manager scope model.
- Refusal correctness means retrieval returned no evidence for a refusal row. It is not answer-level refusal generation.
- Scoped hard negatives may still retrieve unrelated pages because the current raw vector route has no semantic abstention gate.
