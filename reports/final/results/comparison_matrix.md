# Comparison Matrix Input Artifact

This file is an input for a later final-report writing pass. It is not final report prose and should not be cited as a real-corpus benchmark.

## Comparator Boundaries

| Comparator | Status | Evidence Metric Boundary | Existing Evidence Source |
| --- | --- | --- | --- |
| Keyword overlap baseline | Quantitative synthetic row | Same 12-question fixture: Recall@1 88.9%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%. It is a weak deterministic title/caption token-overlap comparator, not an LLM, BM25, VisRAG, real-PDF, or real-corpus benchmark. | `reports/final/results/keyword_baseline_metrics.md`; `eval/retrieval/results/keyword-baseline.*` |
| Visual API baseline | Quantitative synthetic row | Synthetic smoke corpus only: Recall@1 77.8%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%. Not a real-PDF, real-VisRAG, or real-local-corpus benchmark. | `reports/final/results/baseline_metrics.md` (`node1-baseline`) |
| BM25 text manifest | Quantitative synthetic row | Synthetic text-manifest corpus only: Recall@1 88.9%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 100.0%. Not a real-PDF, real-corpus, hybrid, RRF, or VisRAG benchmark. | `reports/final/results/bm25_metrics.md` (`bm25-baseline`) |
| Hybrid page fusion | Quantitative synthetic row | Synthetic hybrid fixture baseline only: Recall@1 77.8%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%, both-trace units 27. Not a real-PDF or real-corpus improvement benchmark. | `reports/final/results/hybrid_metrics.md` (`hybrid-baseline`) |
| Bounded evidence agent | Deterministic trace/regression row | Trace stops, no-new-evidence behavior, citation stripping, packet limits, accepted evidence IDs, evidence deltas, stop reasons, and validated final packets. Not a Recall@k row unless the eval harness is extended to score agent retrieval outputs. | `reports/final/results/agent_trace_examples.md` plus backend regression tests |

## Future Report Table Guidance

- Keep percentage metrics only on measured synthetic retrieval rows.
- Keep GPT-only/manual narrative, Elicit, and Consensus as qualitative market or workflow context unless they are run on the same fixture protocol.
- Represent the bounded evidence agent as a trace/regression comparator, not as a retrieval benchmark row.
- If the later report combines these rows in one table, use a companion `Metric type` or `Boundary` column so measured retrieval metrics and qualitative context are visibly different.
- Do not describe any row here as real local-corpus, real-PDF, real-VisRAG quality, systematic-review completeness, OCR robustness, or dense semantic retrieval performance.
