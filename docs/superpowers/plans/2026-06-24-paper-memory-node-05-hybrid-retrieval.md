# PaperMemory Node 5 Hybrid Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fuse BM25 text hits and VisRAG visual page hits into validated, page-canonical `EvidencePacket`s.

**Architecture:** Node 5 adds an additive hybrid retrieval path while preserving the current visual `/retrieval/search` default behavior. BM25 and VisRAG candidates are collapsed to `(paper_id, page_number)`, combined with Reciprocal Rank Fusion, and emitted as page-level evidence units with source scores and rank traces. Chat consumption and UI display remain Node 6.

**Tech Stack:** Python 3.12 stdlib, FastAPI dependency injection, Pydantic v2, existing `VectorStore`, `VisRAGService`, Node 3 `TextManifestStore`, Node 4 `TextRetriever`, pytest, existing `eval/retrieval/run_retrieval_eval.py`.

---

## Stage Boundary

Node 5 creates the first page-canonical hybrid retrieval path. It must not rewrite chat generation, change the default visual retrieval behavior, add UI, add multi-pass agent orchestration, add dense text embeddings, or claim real-corpus quality beyond the tested synthetic/fixture corpus.

## Latest-Code Surfaces To Preserve

- `/retrieval/search` currently returns `RetrievalResponse` with `evidence` and additive `evidence_packet`.
- The default retrieval route remains visual/vector retrieval unless the request explicitly asks for hybrid retrieval.
- `PageEvidence` remains backward-compatible for existing clients.
- `EvidencePacket` stays public and path-redacted through `validate_evidence_packet`.
- Node 3 text manifests remain the only text corpus source.
- Node 4 `TextRetriever` remains BM25-only and does not call VisRAG or Qdrant.
- Node 6 remains responsible for chat/context/UI consumption of hybrid packets.

## File Map

- Create: `apps/api/app/services/evidence_resolver.py`
  - Owns page-canonical candidate conversion and packet unit construction.
  - Converts visual `PageEvidence` and text `TextSearchHit` into page candidates.
  - Preserves best text snippet, image URL, source ranks, source scores, and RRF score.
- Create: `apps/api/app/services/hybrid_retrieval_service.py`
  - Owns visual search, manifest loading, BM25 search, page-level RRF, limits, and validated `EvidencePacket` output.
- Test: `apps/api/tests/test_hybrid_retrieval_service.py`
  - Covers visual-only, text-only, hybrid overlap, dedupe, paper scope, missing manifests, RRF ordering, and route additive behavior if route wiring is included.
- Modify: `apps/api/app/schemas/retrieval.py`
  - Add an optional retrieval mode field such as `retrieval_mode: Literal["visual", "hybrid"] = "visual"` without changing existing defaults.
- Modify: `apps/api/app/routers/retrieval.py`
  - Add dependencies for `TextManifestStore` and hybrid service only when `retrieval_mode == "hybrid"`.
  - Keep existing visual branch byte-for-byte equivalent where practical.
- Update: `eval/retrieval/run_retrieval_eval.py`
  - Add `hybrid-synthetic` mode while preserving `synthetic` and `bm25-synthetic`.
- Generate:
  - `eval/retrieval/results/hybrid-baseline.json`
  - `eval/retrieval/results/hybrid-baseline.csv`
  - `eval/retrieval/results/hybrid-baseline.md`
- Update:
  - `reports/final/results/hybrid_metrics.md`
  - `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`

## Hybrid Contract

Define small internal models in `hybrid_retrieval_service.py` or `evidence_resolver.py`:

```python
class HybridRetrievalResult(BaseModel):
    status: Literal["success", "partial"]
    evidence: list[PageEvidence]
    evidence_packet: EvidencePacket
    limits: list[str]
    stats: dict[str, int | float]
```

The public route may continue returning `RetrievalResponse`; the hybrid result should be converted into that shape.

RRF behavior:

- Canonical key is `(paper_id, page_number)`.
- Use source ranks, not raw scores, for fusion.
- Use a simple constant `rrf_k=60`.
- Page RRF score is:

```python
sum(1.0 / (rrf_k + rank) for each source rank present)
```

- Preserve raw source scores separately in `EvidenceUnit.rank_trace` and/or metadata.
- A page present in both visual and text channels should produce one hybrid evidence unit, not duplicates.
- A text-only page should still produce an evidence unit with `source="hybrid_page"` and a text snippet.
- A visual-only page should still produce an evidence unit with `source="hybrid_page"` and page image/caption data.

## Evidence Packet Requirements

Each accepted hybrid page must include:

- `EvidenceUnit.source == "hybrid_page"`
- deterministic `evidence_id` derived from `source="hybrid_page"`
- `score` set to RRF score
- `rank_trace` entries for available sources:
  - visual entry: `retriever="visrag"`, `source="visrag_page"`, visual rank, visual score
  - text entry: `retriever="bm25"`, `source="text_page"`, BM25 rank, BM25 score
- `caption` containing the best available snippet/caption:
  - prefer BM25 snippet for text-supported hits
  - otherwise preserve visual caption
- public `image_url` where available through `PageEvidence`
- metadata keys as strings only, with path-like values excluded or redacted by existing validators

Then call `validate_evidence_packet(..., paper_scope=request.paper_ids)` before returning.

## Retrieval Service Contract

`HybridRetrievalService` should expose a focused API such as:

```python
class HybridRetrievalService:
    async def search(
        self,
        *,
        query: str,
        paper_ids: list[str] | None,
        top_k: int,
        score_threshold: float | None = None,
        max_per_paper: int | None = None,
    ) -> HybridRetrievalResult: ...
```

Implementation constraints:

- If `paper_ids` is `None`, preserve the existing unscoped visual behavior only if the current route allows it; otherwise follow the route's no-scope handling.
- If `paper_ids == []`, return no evidence and a validated empty packet.
- Load manifests only for selected paper IDs; missing manifests should add a limit such as `"Text manifest missing for one or more scoped papers."` and continue with visual hits.
- BM25 must search only loaded manifests and selected `paper_ids`.
- Visual search must use the existing `visrag.embed_query(...)` and `vector_store.search_pages(...)` path.
- Apply `max_per_paper` after fusion if provided.
- Sort final pages by descending RRF score, then deterministic `(paper_id, page_number)`.
- Do not call chat/model generation.

## Evaluation Contract

Extend `eval/retrieval/run_retrieval_eval.py` without breaking:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
python eval/retrieval/run_retrieval_eval.py --mode bm25-synthetic --output-prefix bm25-baseline
```

Add:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode hybrid-synthetic --output-prefix hybrid-baseline
```

Hybrid eval should:

- Reuse the existing synthetic vector store and synthetic text manifests.
- Run the hybrid service or equivalent service-level helper directly, not chat.
- Write JSON, CSV, Markdown, and `reports/final/results/hybrid_metrics.md`.
- Include Recall@1, Recall@3, Recall@5, citation-page correctness, refusal correctness, and source coverage counts.
- Label output as synthetic hybrid retrieval over fixtures, not a real-corpus benchmark.
- Include at least one example where hybrid combines visual and text traces for the same final page.

## Required Commands

```powershell
python -m pytest apps/api/tests/test_hybrid_retrieval_service.py -q
python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_text_retriever.py apps/api/tests/test_public_evidence_response.py -q
python eval/retrieval/run_retrieval_eval.py --mode hybrid-synthetic --output-prefix hybrid-baseline
python -m json.tool eval/retrieval/results/hybrid-baseline.json
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
python eval/retrieval/run_retrieval_eval.py --mode bm25-synthetic --output-prefix bm25-baseline
```

## Subagent Plan

### Subagent A: Hybrid Retriever Implementer

**Role:** worker.

**Write scope:** files listed in File Map.

**Task:** Implement page-canonical hybrid retrieval, route opt-in, tests, eval outputs, and report/planning updates.

- [ ] Add a failing service test for overlapping visual and BM25 hits deduped to one page with both rank traces.
- [ ] Add failing tests for visual-only, text-only, empty scope, missing manifest, paper-scope isolation, and `max_per_paper`.
- [ ] Create `evidence_resolver.py` with page-canonical candidate conversion and packet unit construction.
- [ ] Create `hybrid_retrieval_service.py` with visual search, manifest loading, BM25 search, RRF, limits, and validated packet output.
- [ ] Add optional `retrieval_mode` to `RetrievalQuery` with default `"visual"`.
- [ ] Wire `/retrieval/search` to call hybrid retrieval only when `retrieval_mode == "hybrid"`.
- [ ] Extend eval runner with `hybrid-synthetic`.
- [ ] Generate `hybrid-baseline.*` outputs and `hybrid_metrics.md`.
- [ ] Update durable planning files.
- [ ] Run all required commands.

### Subagent B: Node 5 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check implementation against this stage plan and source superplan Node 5.

- [ ] Verify default visual `/retrieval/search` behavior remains available.
- [ ] Verify hybrid mode fuses BM25 and VisRAG at `(paper_id, page_number)`, not text chunk/span level.
- [ ] Verify overlapping pages are deduped and preserve both source rank traces.
- [ ] Verify text-only, visual-only, and hybrid-overlap cases all produce validated packets.
- [ ] Verify selected `paper_ids` scope cannot leak.
- [ ] Verify eval runner preserves `synthetic` and `bm25-synthetic` modes and adds `hybrid-synthetic`.
- [ ] Verify no chat/UI/multi-pass agent changes slipped into Node 5.
- [ ] Verify task_plan status is not final-complete before reviews pass.

### Subagent C: Node 5 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability, correctness, and claim boundaries.

- [ ] Confirm RRF implementation is simple, deterministic, and source-rank based.
- [ ] Confirm page-canonical aggregation avoids duplicate page inflation.
- [ ] Confirm evidence metadata does not leak local paths.
- [ ] Confirm missing manifests degrade gracefully instead of failing hybrid retrieval.
- [ ] Confirm tests exercise behavior, not implementation trivia.
- [ ] Confirm report wording says synthetic hybrid fixture baseline, not real-corpus improvement.
- [ ] Confirm Node 6 chat/UI and Node 7 orchestrator work are not preimplemented.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 5:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 5 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 5 Gate

Node 5 is accepted only when:

- All required commands pass.
- Spec review passes.
- Quality review passes.
- Hybrid output is page-canonical and measurable.
- Existing visual and BM25 synthetic eval modes still work.
- `reports/final/results/hybrid_metrics.md` explains the hybrid baseline and limitations.
- The next stage is still Node 6: Verified Chat And Evidence UI.
