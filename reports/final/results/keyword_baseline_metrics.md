# Keyword Overlap Baseline Metrics

## Methods And Evaluation Setup

| Field | Keyword baseline setup |
| --- | --- |
| Evaluation surface | Deterministic local function in `eval/retrieval/run_retrieval_eval.py` |
| Corpus mode | Existing synthetic pages from `synthetic_pages()` |
| Corpus size | 4 synthetic papers, 12 synthetic pages |
| Question set | 12 golden questions from `eval/retrieval/golden_questions.jsonl`, including 3 refusal/negative cases (25.0%) |
| Retrieval path | Tokenize question and page title+caption with `TOKEN_RE`; score by unique token overlap; tie-break by `paper_id`, then `page_number` |
| Metrics | Recall@1, Recall@3, Recall@5, citation-page correctness, retrieval-level refusal correctness |
| Citation grain | Page-level `(paper_id, page_number)` correctness only |

## Keyword Baseline Row

| Run | Mode | Recall@1 | Recall@3 | Recall@5 | Citation-page correctness | Refusal correctness | Boundary |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| keyword-baseline | keyword overlap baseline | 88.9% | 100.0% | 100.0% | 100.0% | 33.3% | Not an LLM, BM25, VisRAG, real-PDF, or real-corpus benchmark |

## Limitations

- This is a weak deterministic same-fixture comparator, not a model or production retriever.
- It measures only title/caption token overlap on the synthetic fixture.
- It returns no pages for empty paper scope or zero positive overlap.
- Refusal correctness is retrieval-level no-hit behavior; answer-level abstention is outside this run.
