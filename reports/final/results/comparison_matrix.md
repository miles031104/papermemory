# Comparison Matrix Input Artifact

This file is an input for a later final-report writing pass. It is not final report prose and should not be cited as a real-corpus benchmark.

## Comparator Boundaries

| Comparator | Status | Evidence Metric Boundary | Existing Evidence Source |
| --- | --- | --- | --- |
| Realistic cross-document retrieval | Quantitative controlled fixture | Five user-facing questions over the skill-security demo corpus compare Keyword overlap, VisRAG page-image retrieval, BM25 text-manifest retrieval, and Hybrid page fusion using evidence recall@5 and full support@5. The fixture supports a controlled evidence-coverage comparison, not a broad scholarly-corpus benchmark. | `reports/final/results/realistic_crossdoc_metrics.md`; `eval/retrieval/results/realistic-crossdoc.*` |
| Bounded evidence agent | Deterministic trace/regression row | Trace stops, no-new-evidence behavior, citation stripping, packet limits, accepted evidence IDs, evidence deltas, stop reasons, and validated final packets. Not a Recall@k row unless the eval harness is extended to score agent retrieval outputs. | `reports/final/results/agent_trace_examples.md` plus backend regression tests |

## Future Report Table Guidance

- Keep percentage metrics only on measured retrieval rows with a shared fixture and shared metrics.
- Keep GPT-only/manual narrative, Elicit, and Consensus as qualitative market or workflow context unless they are run on the same fixture protocol.
- Represent the bounded evidence agent as a trace/regression comparator, not as a retrieval benchmark row.
- Do not describe any row here as real local-corpus, real-PDF, real-VisRAG quality, systematic-review completeness, OCR robustness, or dense semantic retrieval performance.
