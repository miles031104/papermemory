# Keyword Overlap Baseline

Mode: deterministic keyword overlap over synthetic fixture pages.

This run tokenizes each golden question and each allowed synthetic page title plus caption with `TOKEN_RE`, scores pages by unique token overlap count, and sorts by descending overlap, then `paper_id`, then `page_number`. It is not an LLM baseline, BM25 baseline, VisRAG result, real-PDF result, or real-corpus benchmark.

## Metrics

| Metric | Value |
| --- | ---: |
| Questions | 12 |
| Negative/refusal share | 25.0% |
| Recall@1 | 88.9% |
| Recall@3 | 100.0% |
| Recall@5 | 100.0% |
| Citation-page correctness | 100.0% |
| Refusal correctness | 33.3% |

## Per-Question Results

| ID | Type | Expected | Keyword top pages | R@5 | Cite pages correct | Refusal correct |
| --- | --- | --- | --- | ---: | --- | --- |
| gq-001 | single_paper_fact | demo-visrag-core:1 | demo-visrag-core:1, demo-visrag-core:3, demo-visrag-core:2 | 100.0% | yes | n/a |
| gq-002 | single_paper_fact | demo-visrag-core:2 | demo-visrag-core:2, demo-visrag-core:1, demo-visrag-core:3 | 100.0% | yes | n/a |
| gq-003 | single_paper_fact | demo-bm25-text:1 | demo-bm25-text:1, demo-bm25-text:2, demo-bm25-text:3 | 100.0% | yes | n/a |
| gq-004 | single_paper_fact | demo-bm25-text:2 | demo-bm25-text:2, demo-bm25-text:1 | 100.0% | yes | n/a |
| gq-005 | single_paper_fact | demo-bm25-text:3 | demo-bm25-text:3, demo-bm25-text:1, demo-bm25-text:2 | 100.0% | yes | n/a |
| gq-006 | multi_page_within_paper | demo-agentic-rag:1, demo-agentic-rag:2 | demo-agentic-rag:1, demo-agentic-rag:2, demo-agentic-rag:3 | 100.0% | yes | n/a |
| gq-007 | multi_paper_comparison | demo-bm25-text:1, demo-visrag-core:1 | demo-bm25-text:1, demo-visrag-core:1, demo-bm25-text:2, demo-bm25-text:3, demo-visrag-core:2 | 100.0% | yes | n/a |
| gq-008 | metric_definition | demo-risk-eval:2 | demo-risk-eval:2, demo-risk-eval:3, demo-risk-eval:1 | 100.0% | yes | n/a |
| gq-009 | single_paper_fact | demo-risk-eval:3 | demo-risk-eval:3, demo-risk-eval:2 | 100.0% | yes | n/a |
| gq-010 | refusal_missing_evidence | n/a | demo-visrag-core:1, demo-agentic-rag:2, demo-agentic-rag:3, demo-risk-eval:2, demo-risk-eval:3 | n/a | n/a | no |
| gq-011 | refusal_empty_scope | n/a | none | n/a | n/a | yes |
| gq-012 | refusal_missing_evidence | n/a | demo-risk-eval:3, demo-risk-eval:2 | n/a | n/a | no |

## Boundary

- Keyword scoring is exact token overlap, not BM25 term weighting or semantic retrieval.
- The corpus is the existing synthetic fixture pages from `synthetic_pages()`.
- The question set is `eval/retrieval/golden_questions.jsonl`.
- If `paper_ids` is empty, or no allowed page has positive overlap, the baseline returns no pages.
- Refusal correctness is retrieval-level no-hit behavior, not answer-level refusal generation.
