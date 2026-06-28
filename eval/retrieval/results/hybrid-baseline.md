# Node 5 Hybrid Retrieval Baseline

Mode: synthetic hybrid fixture baseline.

This run calls `HybridRetrievalService` directly with the synthetic VisRAG vector store and synthetic Node 3 text manifests. It fuses page-level visual and BM25 ranks with RRF at canonical `(paper_id, page_number)` grain. This is not a real-PDF, real-corpus, or real-corpus improvement benchmark.

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
| Units with both traces | 27 |
| Visual-only units | 10 |
| Text-only units | 0 |

## Per-Question Results

| ID | Type | Expected | Hybrid top pages | R@5 | Cite pages correct | Refusal correct | Source coverage |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| gq-001 | single_paper_fact | demo-visrag-core:1 | demo-visrag-core:1, demo-visrag-core:3, demo-visrag-core:2 | 100.0% | yes | n/a | both=3; visual_only=0; text_only=0 |
| gq-002 | single_paper_fact | demo-visrag-core:2 | demo-visrag-core:2, demo-visrag-core:1, demo-visrag-core:3 | 100.0% | yes | n/a | both=3; visual_only=0; text_only=0 |
| gq-003 | single_paper_fact | demo-bm25-text:1 | demo-bm25-text:1, demo-bm25-text:2, demo-bm25-text:3 | 100.0% | yes | n/a | both=2; visual_only=1; text_only=0 |
| gq-004 | single_paper_fact | demo-bm25-text:2 | demo-bm25-text:2, demo-bm25-text:1, demo-bm25-text:3 | 100.0% | yes | n/a | both=3; visual_only=0; text_only=0 |
| gq-005 | single_paper_fact | demo-bm25-text:3 | demo-bm25-text:2, demo-bm25-text:3, demo-bm25-text:1 | 100.0% | yes | n/a | both=3; visual_only=0; text_only=0 |
| gq-006 | multi_page_within_paper | demo-agentic-rag:1, demo-agentic-rag:2 | demo-agentic-rag:1, demo-agentic-rag:2, demo-agentic-rag:3 | 100.0% | yes | n/a | both=3; visual_only=0; text_only=0 |
| gq-007 | multi_paper_comparison | demo-bm25-text:1, demo-visrag-core:1 | demo-bm25-text:1, demo-visrag-core:1, demo-bm25-text:2, demo-visrag-core:3, demo-visrag-core:2 | 100.0% | yes | n/a | both=5; visual_only=0; text_only=0 |
| gq-008 | metric_definition | demo-risk-eval:2 | demo-risk-eval:2, demo-risk-eval:1, demo-risk-eval:3 | 100.0% | yes | n/a | both=3; visual_only=0; text_only=0 |
| gq-009 | single_paper_fact | demo-risk-eval:3 | demo-risk-eval:3, demo-risk-eval:2, demo-risk-eval:1 | 100.0% | yes | n/a | both=2; visual_only=1; text_only=0 |
| gq-010 | refusal_missing_evidence | n/a | demo-agentic-rag:2, demo-agentic-rag:3, demo-risk-eval:1, demo-risk-eval:3, demo-risk-eval:2 | n/a | n/a | no | both=0; visual_only=5; text_only=0 |
| gq-011 | refusal_empty_scope | n/a | none | n/a | n/a | yes | both=0; visual_only=0; text_only=0 |
| gq-012 | refusal_missing_evidence | n/a | demo-risk-eval:2, demo-risk-eval:1, demo-risk-eval:3 | n/a | n/a | no | both=0; visual_only=3; text_only=0 |

## Boundary

- Hybrid scores are RRF scores from source ranks with `k=60`, not calibrated relevance probabilities.
- Source traces preserve visual and BM25 source ranks and raw scores inside `EvidencePacket.units[].rank_trace`.
- This is a synthetic fixture baseline over stable aliases and fixture captions, not a real-corpus improvement claim.
- Chat/context/UI consumption remains deferred to Node 6.
