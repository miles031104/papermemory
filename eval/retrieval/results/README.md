# Retrieval Eval Results

This directory stores generated Node 1 retrieval evaluation outputs.

Default command:

```bash
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
```

Node 1 currently uses a deterministic synthetic smoke corpus because this
checkout has no real local PDFs under `storage/papers/`. The runner still calls
the current FastAPI `POST /retrieval/search` route through `TestClient`
dependency overrides and seeds page-level evidence through the current
`VectorStore` interface.

Generated files:

- `node1-baseline.json`: full run metadata, synthetic corpus, metrics, and per-question results.
- `node1-baseline.csv`: compact per-question table for spreadsheet checks.
- `node1-baseline.md`: readable baseline summary.

Interpretation boundary:

- These outputs validate the measurement spine and API contract.
- They are not a real-PDF, real-VisRAG, or real-local-corpus benchmark.
- Refusal correctness means retrieval returned no evidence for a refusal row; it is not answer-level refusal generation.
