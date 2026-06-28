# PaperMemory Node 4 BM25 Retriever Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local, explainable, BM25-only page text retriever over Node 3 text manifests and export a measurable BM25 baseline row.

**Architecture:** Node 4 consumes persisted `TextManifest` data and returns page-level lexical hits with snippets and source ranks. It is independent from VisRAG and does not replace `/retrieval/search`; hybrid fusion is deferred to Node 5. Evaluation writes BM25-only output files separate from the Node 1 visual/synthetic baseline.

**Tech Stack:** Python 3.12 stdlib, Pydantic v2, Node 3 `TextManifest`, pytest, existing `eval/retrieval/run_retrieval_eval.py`.

---

## Stage Boundary

Node 4 adds a cheap lexical retrieval channel only. It must not implement RRF/hybrid fusion, change current VisRAG retrieval ranking, wire BM25 into chat by default, add UI, or claim real-corpus retrieval quality beyond the tested fixture/synthetic manifest baseline.

## Latest-Code Surfaces To Preserve

- Current `/retrieval/search` remains visual/vector retrieval.
- Node 1 `node1-baseline.*` files remain the visual/synthetic baseline.
- Node 2 `EvidencePacket` remains page-grain and additive.
- Node 3 manifests remain the source of text documents.
- BM25 scores remain separate from visual scores and do not get fused in this node.

## File Map

- Create: `apps/api/app/services/text_retriever.py`
  - Owns BM25 tokenization, document building from `TextManifest`, scoring, snippet selection, and `TextSearchHit`.
- Test: `apps/api/tests/test_text_retriever.py`
  - Exact method/dataset/abbreviation/citation-token retrieval; no external model calls; paper scope behavior; snippets/ranks.
- Update: `eval/retrieval/run_retrieval_eval.py`
  - Add BM25-only eval mode or option that writes independent BM25 result files.
  - Keep existing synthetic visual baseline behavior intact.
- Update or create generated outputs:
  - `eval/retrieval/results/bm25-baseline.json`
  - `eval/retrieval/results/bm25-baseline.csv`
  - `eval/retrieval/results/bm25-baseline.md`
- Update: `reports/final/results/bm25_metrics.md`
  - Report-ready BM25 baseline row and text retrieval discussion.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - Commands, outcomes, review results.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
  - Node 4 status only after implementation/review gates.

## Retriever Contract

`TextSearchHit` should include:

- `paper_id: str`
- `page_number: int`
- `score: float`
- `rank: int`
- `snippet: str | None`
- `matched_terms: list[str]`
- `source: Literal["bm25_text"]`

`TextRetriever` should expose a small API such as:

```python
class TextRetriever:
    @classmethod
    def from_manifests(cls, manifests: Sequence[TextManifest]) -> "TextRetriever": ...

    def search(
        self,
        query: str,
        *,
        paper_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[TextSearchHit]: ...
```

Implementation constraints:

- Use a simple local BM25 formula with term frequency, inverse document frequency, document length, `k1=1.5`, `b=0.75`.
- Tokenization should be deterministic and handle method names, dataset names, abbreviations, and citation-like tokens.
- Documents are page-level, built from `PageTextEntry.text` and optionally block text.
- Skip pages where `quality.has_text` is false.
- Preserve page-grain output; text spans/snippet evidence may be used for display but fusion remains Node 5.
- If query has no tokens or scope is empty, return no hits.

## Evaluation Contract

Update `eval/retrieval/run_retrieval_eval.py` without breaking the existing command:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
```

Add a BM25 command such as:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode bm25-synthetic --output-prefix bm25-baseline
```

BM25 eval should:

- Build synthetic text manifests aligned with existing golden fixture paper/page IDs.
- Run `TextRetriever` directly; it does not call VisRAG, Qdrant, or `/retrieval/search`.
- Write JSON, CSV, and Markdown results under `eval/retrieval/results/`.
- Include Recall@1, Recall@3, Recall@5, citation-page correctness where applicable, and refusal correctness where applicable.
- Label output as a synthetic BM25-only baseline, not a real-corpus benchmark.

## Subagent Plan

### Subagent A: BM25 Retriever Implementer

**Role:** worker.

**Write scope:** files listed in File Map.

**Task:** Implement page-level BM25 retrieval over manifests, add tests, extend eval runner with a BM25-only mode, generate BM25 outputs, and update report/planning files.

- [ ] Create `apps/api/app/services/text_retriever.py`.
- [ ] Add deterministic tokenization and local BM25 scoring.
- [ ] Add snippets and matched terms.
- [ ] Add tests in `apps/api/tests/test_text_retriever.py`.
- [ ] Extend `eval/retrieval/run_retrieval_eval.py` with `bm25-synthetic` mode while preserving existing synthetic mode.
- [ ] Generate `bm25-baseline.*` result files.
- [ ] Update `reports/final/results/bm25_metrics.md`.
- [ ] Run required commands and update planning files.

Required commands:

```powershell
python -m pytest apps/api/tests/test_text_retriever.py -q
python eval/retrieval/run_retrieval_eval.py --mode bm25-synthetic --output-prefix bm25-baseline
python -m json.tool eval/retrieval/results/bm25-baseline.json
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
python -m pytest apps/api/tests/test_page_text_extractor.py apps/api/tests/test_text_manifest_store.py apps/api/tests/test_evidence_contract.py -q
```

### Subagent B: Node 4 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check implementation against this stage plan and source superplan Node 4.

- [ ] Verify exact method, dataset, abbreviation, and citation-token queries retrieve expected pages.
- [ ] Verify BM25 runs without external model calls, Qdrant, or VisRAG.
- [ ] Verify BM25 hits are page-level with snippets, matched terms, rank, and separate BM25 score.
- [ ] Verify eval runner produces BM25-only JSON/CSV/Markdown and report row.
- [ ] Verify existing Node 1 synthetic command still works.
- [ ] Verify no hybrid/RRF/chat/UI wiring slipped in.

### Subagent C: Node 4 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability, correctness, and claim boundaries.

- [ ] Confirm BM25 implementation is simple, deterministic, and local.
- [ ] Confirm tokenization is stable and useful for paper terms without overengineering.
- [ ] Confirm snippets do not invent text and preserve page provenance.
- [ ] Confirm scope filtering cannot leak papers outside selected `paper_ids`.
- [ ] Confirm report wording says BM25-only synthetic baseline, not retrieval quality improvement over real corpus.
- [ ] Confirm Node 5 hybrid work is not preimplemented.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 4:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 4 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 4 Gate

Node 4 is accepted only when:

- All required commands pass.
- Spec review passes.
- Quality review passes.
- BM25-only retrieval is measurable.
- Existing visual/synthetic baseline command still works.
- `reports/final/results/bm25_metrics.md` explains BM25 baseline and limitations.
- The next stage is still Node 5: Page-Canonical Hybrid Retrieval.
