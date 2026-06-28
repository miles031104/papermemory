# PaperMemory Evidence Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Build PaperMemory into a local-first compound AI research assistant that helps researchers find, verify, and package evidence across multiple PDFs. The product promise is deliberately narrow and commercial: PaperMemory does not replace researchers or complete full systematic reviews; it replaces the expensive first-pass evidence gathering and citation-packaging loop while preserving human verification through citation-grounded evidence packets.

The fastest high-score path is:

1. Prove baseline retrieval and reliability with a small but reproducible golden set.
2. Add a stable evidence contract before adding more agent behavior.
3. Add lightweight text evidence with PyMuPDF plus BM25.
4. Fuse text and visual retrieval at the page level with RRF while keeping VisRAG as the visual path.
5. Add a bounded, three-pass evidence-seeking state machine with structured outputs and measurable evidence deltas.
6. Convert the system behavior into report assets: baseline table, robustness matrix, cost-benefit analysis, and road-show demo.

## Current Status

This is v3, adapted to the latest remote implementation baseline while preserving the v2 execution order and deliverable gates. The v2 plan was finalized after five independent feasibility audits and one final report/demo-oriented plan audit:

- Cicero audited evidence contracts and evaluation design.
- Herschel audited PyMuPDF text extraction and BM25 retrieval.
- Noether audited visual retrieval, RRF, and hybrid fusion.
- Erdos audited the bounded three-pass agent design.
- Rawls audited profit logic, commercial stress test, and report strategy.

The implementation baseline is now the fast-forwarded remote `origin/miles` commit `6884d738df9d685bad4f5a673a7d13a7bc2fb691` (`feat: expand paper manager and agentic retrieval`). The synced baseline already includes group-scoped paper management, `PageEvidence` redaction and image URLs, extracted page text stored as captions in vector payloads, SSE streaming chat, early evidence frames, citation cleanup, and a narrow bounded query planner over VisRAG page search. Future implementation should treat those features as existing surfaces to extend, not rebuild from scratch.

The final target is not only a working feature. The final target is:

1. A NeurIPS-style final report that proves technical quality, need, reliability, reproducibility, and commercial value.
2. A polished 3-minute road-show demo video that shows the compound AI system solving a real research evidence task.

## Core Architecture

PaperMemory should remain evidence-contract-first. The latest code already has this baseline route:

```text
PDF upload
  -> PyMuPDF page render plus extracted page text captions
  -> VisRAG page-image index in Qdrant
  -> selected group paper scope
  -> bounded LLM query planning over page search
  -> PageEvidence with redacted public fields
  -> SSE/Markdown chat answer with page citations and limits
```

The target route keeps the same product direction but upgrades the evidence layer:

```text
PDF upload
  -> page images and metadata
  -> PyMuPDF text manifest with quality flags
  -> VisRAG page-image index
  -> BM25 page-text index
  -> page-canonical hybrid retrieval
  -> validated EvidencePacket
  -> bounded evidence-seeking orchestrator
  -> cited answer with limits/refusal
```

### Evidence Objects

`EvidenceUnit v0` is the atomic contract. It should include:

- `evidence_id`
- `paper_id`
- `page_number`
- `canonical_page_id`
- `modality`: `text`, `visual`, or `hybrid`
- `source`: `bm25`, `visrag`, `neighbor`, `manual_eval`, etc.
- `text_span` or `text_snippet`, nullable
- `image_url` or redacted image reference
- `score`, `rank`, `source_rank`, `rrf_score`
- `text_quality`, `ocr_needed`
- `metadata`

`EvidencePacket` is the unit consumed by chat and the agent. It should include ordered evidence units, query metadata, source counts, rank trace, validation status, limits, and trace-safe diagnostics.

Fine-grained `bbox`, `crop_image_path`, section labels, OCR text, and ColPali-style multi-vector evidence should be optional future fields, not blockers for v1.

### Hybrid Retrieval Rule

The canonical fusion unit for v1 is `(paper_id, page_number)`, not arbitrary text chunks. BM25 may return spans or block groups, and VisRAG returns page images, but fusion should first collapse candidates to pages:

1. BM25 returns text spans, then aggregates best spans per page.
2. VisRAG returns visual page candidates.
3. RRF fuses by source rank at the page level.
4. The final `EvidencePacket` attaches the best text spans and page image for each accepted page.

This avoids over-rewarding pages that happen to split into many text chunks.

### Bounded Agent Rule

The agent should be a server-verified state machine, not free-form ReAct:

```text
QueryRewrite -> FirstRetrieval -> EvidenceAnalysis -> SecondRetrieval
  -> SufficiencyCheck -> FinalRetrieval -> Answer
```

The LLM may only emit structured JSON decisions such as `next_query`, `retrieval_mode`, `missing_evidence`, `stop_reason`, and `confidence_band`. The server executes retrieval, fusion, dedupe, validation, and budget clamps.

Hard invariants:

- Max 3 retrieval passes.
- Max 4 query variants per pass.
- Max 8 final evidence units.
- Max 3 attached page images.
- A follow-up pass must add a measurable evidence delta: new `paper_id/page/source/span-or-page hash`.
- If the second pass adds no useful evidence, go to sufficiency/refusal.
- Final answers may cite only accepted evidence IDs.
- Hidden chain-of-thought is never shown; the UI shows trace-safe actions, evidence IDs, limits, and validation outcomes.

## File Map

Existing latest-code surfaces to preserve:

- `apps/api/app/schemas/retrieval.py`: current public `PageEvidence`, retrieval query stats, image URL filling, caption and metadata redaction.
- `apps/api/app/schemas/chat.py`: current `ChatRequest` with `score_threshold`, `max_per_paper`, `enable_query_rewrite`, and default-on `enable_agentic_retrieval`.
- `apps/api/app/services/chat_service.py`: current single-pass retrieval, bounded query planner, zero-result retry, SSE `answer_stream`, citation cleanup, and conversation summarization.
- `apps/api/app/services/context_builder.py`: current bounded planner prompt and EVisRAG-style page-evidence prompt.
- `apps/api/app/services/ingestion_service.py`, `indexing_service.py`, and `vector_store.py`: current page rendering, page text captions, Qdrant payloads, scoped page search, score threshold, and per-paper cap.
- `apps/api/app/routers/chat.py` and `retrieval.py`: current non-streaming/streaming chat and retrieval endpoints.
- `apps/web/lib/api.ts`, `types.ts`, and `use-chat-session.ts`: current streaming chat client, early evidence frame handling, and default agentic retrieval request.
- `apps/web/components/chat-panel.tsx` and `evidence-panel.tsx`: current Markdown answer rendering, clickable citation chips, evidence cards, and page-image preview.
- `apps/api/app/services/workspace_store.py` plus workspace/paper routers and UI: current library/group scope, move/delete, and Paper Manager flows.

New or adapted surfaces:

- Create `apps/api/app/schemas/evidence.py`: `EvidenceUnit`, `EvidencePacket`, citations, rank trace, source metadata, and adapters from current `PageEvidence`.
- Create `apps/api/app/services/evidence_validator.py`: schema, page existence, citation containment, scope, path redaction, and public-response validation.
- Create `apps/api/app/services/page_text_extractor.py`: PyMuPDF extraction of page text, blocks, words, page dimensions, and quality stats.
- Create `apps/api/app/services/text_manifest_store.py`: local JSON manifest persistence and reload; keep current vector captions as a display fallback.
- Create `apps/api/app/services/text_retriever.py`: `TextRetriever` interface plus BM25 implementation over persisted manifests.
- Create `apps/api/app/services/evidence_resolver.py`: text hit -> page image; visual page hit -> manifest text; neighbor page expansion.
- Create `apps/api/app/services/hybrid_retrieval_service.py`: BM25 + current VisRAG retrieval, page aggregation, RRF, dedupe, packet output.
- Create `apps/api/app/services/research_orchestrator.py`: three-pass state machine that reuses the existing planner concepts but adds pass state, evidence-delta checks, and trace output.
- Modify `apps/api/app/services/indexing_service.py` and `ingestion_service.py`: persist manifests while preserving current caption indexing and ready-status behavior.
- Modify `apps/api/app/services/chat_service.py`: consume verified `EvidencePacket`s internally while preserving existing chat endpoints, SSE frame order, and current conversation mode.
- Modify `apps/api/app/services/context_builder.py`: render compact evidence packets with stable citation IDs while keeping visible Answer/Evidence/Limits behavior.
- Modify `apps/api/app/schemas/retrieval.py` and `apps/api/app/schemas/chat.py`: add packet-aware fields additively so existing `PageEvidence` clients keep working.
- Modify `apps/web/lib/types.ts`, `apps/web/lib/api.ts`, `apps/web/lib/use-chat-session.ts`, `apps/web/components/evidence-panel.tsx`, and `chat-panel.tsx`: display packet metadata and source modality without breaking existing early evidence updates.
- Add eval assets under `apps/api/tests/fixtures/retrieval_eval/` or `eval/retrieval/`.
- Add tests under `apps/api/tests/test_evidence_*.py`, `test_page_text_extractor.py`, `test_text_manifest_store.py`, `test_text_retriever.py`, `test_hybrid_retrieval_service.py`, and `test_research_orchestrator.py`; keep existing `test_chat_service_agentic.py`, `test_chat_streaming.py`, and `test_public_evidence_response.py` as regression gates.
- Create report assets under `reports/final/`: NeurIPS source, figures, tables, result exports, checklist, and appendix material.
- Create demo assets under `demo/`: 3-minute script, shot list, demo question set, screenshots or clips, and final recording checklist.

## Final Plan Audit

| Area | Feasibility | Audit Result | Main Risk | Control |
| --- | --- | --- | --- | --- |
| Baseline eval | High | Current VisRAG path already exists, so retrieval-only metrics can be captured before new implementation. | Hand-picked cases may overfit. | Label first set as golden regression; include negative cases. |
| EvidenceUnit and validators | High | Mostly schema and validation work, well isolated from model behavior. | Overbuilding schema before retrieval exists. | Keep v0 page-level and nullable future fields. |
| PyMuPDF manifest | High | PyMuPDF is already a dependency and supports text/blocks/words. | PDF layout and coordinate drift. | Store page dimensions, quality flags, and `ocr_needed`. |
| BM25 retrieval | High | Can be local and page-level, with no new model serving. | Weak semantic recall. | Treat as lexical complement to VisRAG, not a replacement. |
| Page-level hybrid fusion | Medium-high | RRF is simple and testable with mocked retrievers. | Mixing span-level text with page-level visual hits. | Fuse by `(paper_id, page_number)` first. |
| Verified chat integration | Medium-high | Latest `ChatService`, SSE streaming, Markdown chat UI, citation chips, and evidence panel already exist. | Packet migration could break streaming frame shape or existing `PageEvidence` clients. | Add packet fields additively; keep current SSE order and `PageEvidence` compatibility. |
| Bounded research orchestrator | Medium-high | Latest code already has a bounded JSON query planner over VisRAG search. | Mistaking the existing single-step planner for the planned three-pass orchestrator. | Upgrade the existing planner path into a state machine with evidence deltas and trace output. |
| Robustness package | High | Most cases can be deterministic tests and fixtures. | Real scanned/OCR behavior may be incomplete. | Mark OCR as future work and test `ocr_needed` routing. |
| Commercial stress test | High | Can be computed from eval traces, token estimates, and refreshed price/wage sources. | Pricing changes. | Refresh pricing and wage references immediately before report freeze. |
| Final report | Medium-high | Technical and commercial evidence will be generated by earlier nodes. | Writing claims before results exist. | Maintain `reports/final/results/` exports as the claim boundary. |
| 3-minute demo video | Medium | The demo can be scripted around one successful multi-paper path plus one refusal path. | Live demo instability. | Prepare deterministic seeded demo corpus and backup screenshots/clips. |

## One-Node Execution Protocol

Implementation must proceed one node at a time. A node is complete only when its code or artifact changes, tests/checks, report contribution, and demo contribution are all done.

For every node:

1. Re-read this plan plus `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`.
2. Confirm the node objective and exact file scope.
3. Write or update tests before implementation when code changes are involved.
4. Implement the minimum needed to satisfy the node.
5. Run the node-specific checks.
6. Export or update the report artifact for that node.
7. Update demo notes if the node changes what can be shown.
8. Update `.planning/.../progress.md`, `.planning/.../findings.md` when new facts appear, and node status in `.planning/.../task_plan.md`.

Do not start Node N+1 until Node N passes its exit gate, unless the user explicitly changes the plan.

## Global Acceptance Criteria

The project is complete only when all of these are true:

- The system can ingest a small local PDF corpus, retrieve page-level visual evidence, retrieve text evidence, fuse both into validated `EvidencePacket`s, and answer with citations and limits.
- The bounded agent can run a three-pass retrieve-analyze-retrieve flow with trace-safe visible actions and no exposed hidden reasoning.
- Evaluation exports compare at least GPT-only/manual narrative baseline, current VisRAG, BM25-only, hybrid retrieval, and bounded agent where applicable.
- Robustness tests cover missing evidence, conflicting evidence, empty scope, low-text/scanned pages, prompt-injection PDF text, and citation drift.
- The final report compiles as a single NeurIPS-style PDF with main body at or under nine pages, followed by references, checklist, and appendices.
- The demo package contains a 3-minute script and enough reproducible assets to record a road-show video without relying on luck.

## Implementation Nodes

### Node 0: Repo And Execution Ground Truth

**Objective:** Make implementation safe to begin from the latest remote baseline.

**Files:**
- Read: `README.md`, `AGENT.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/CURRENT_STAGE_OPTIMIZATION_GOALS.md`, `docs/DEVELOPMENT_SUMMARY_2026-05-27.md`, `docs/superpowers/plans/2026-05-27-bounded-agentic-retrieval.md`
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`

**Implementation target:**
- Use remote `origin/miles` commit `6884d738df9d685bad4f5a673a7d13a7bc2fb691` as the implementation baseline.
- Record the chosen branch/commit, Python version, Node version, and test commands.
- Record existing latest-code surfaces that later nodes must preserve: group-scoped paper management, `PageEvidence`, SSE chat, early evidence frames, current query planner, page captions, and public redaction.

**Acceptance checks:**
- `git status --short --branch` is recorded in `progress.md`.
- `npm --prefix apps/web run typecheck` result is recorded.
- `pytest apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_public_evidence_response.py -q` or a smaller justified smoke subset is recorded.
- No feature code is changed in this node.

**Report contribution:** Reproducibility environment note.

**Demo contribution:** Stable local run instructions for recording.

**Exit gate:** The team knows exactly which checkout is the implementation base.

### Node 1: Demo Corpus And Golden Evaluation Harness

**Objective:** Create the measurement spine before improving retrieval.

**Files:**
- Create: `eval/retrieval/golden_questions.jsonl`
- Create: `eval/retrieval/run_retrieval_eval.py`
- Create: `eval/retrieval/results/README.md`
- Create or update: `reports/final/results/baseline_metrics.md`

**Implementation target:**
- Select a small local demo corpus, preferably 8-20 PDFs, using the latest library/group scope model.
- Define 10-15 initial questions, with a path to expand to 20-30.
- Include 20-30% negative cases.
- Export current baseline metrics for raw `/retrieval/search` VisRAG page search and, where useful, current `/chat` bounded query planning over the active group.

**Acceptance checks:**
- Eval fixtures contain `question`, `paper_ids`, `expected_pages`, `answer_key`, `must_cite_pages`, `should_refuse`, and `question_type`.
- Running the eval writes JSON and Markdown/CSV summaries under `eval/retrieval/results/`.
- Metrics include Recall@1, Recall@3, Recall@5, citation-page correctness, and refusal correctness where applicable.
- The demo has one primary multi-paper question and one refusal/missing-evidence question.
- Golden fixtures record both `paper_ids` and optional `group_id`/`library_id` provenance so the eval matches the current Paper Manager scope model.

**Report contribution:** Methods/evaluation setup table and first baseline row.

**Demo contribution:** Locked demo question set.

**Exit gate:** We can rerun the baseline and get the same result files.

### Node 2: EvidenceUnit And EvidencePacket Contract

**Objective:** Create the evidence object all later retrieval and agent work must use.

**Files:**
- Create: `apps/api/app/schemas/evidence.py`
- Create: `apps/api/app/services/evidence_validator.py`
- Modify: `apps/api/app/schemas/retrieval.py`
- Test: `apps/api/tests/test_evidence_contract.py`
- Update: `reports/final/results/evidence_contract.md`

**Implementation target:**
- Add deterministic evidence IDs and adapters from current `PageEvidence`.
- Add validator checks for paper/page/image existence, citation containment, paper scope, and path redaction while preserving current public redaction behavior.
- Keep future fields nullable.

**Acceptance checks:**
- Invalid page references fail validation.
- Citations outside the accepted evidence set fail validation.
- Public response serialization never exposes local absolute paths.
- Existing retrieval/chat tests still pass.
- Existing `PageEvidence` API clients still receive compatible fields; packet data is additive.

**Report contribution:** EvidencePacket schema figure/table.

**Demo contribution:** A visible evidence ID format that can be shown in the UI/video.

**Exit gate:** Every retrieval result can be represented as validated evidence.

### Node 3: PyMuPDF Text Manifest

**Objective:** Add dependable page text evidence without OCR.

**Files:**
- Create: `apps/api/app/services/page_text_extractor.py`
- Create: `apps/api/app/services/text_manifest_store.py`
- Modify: `apps/api/app/services/ingestion_service.py`
- Modify: `apps/api/app/services/indexing_service.py`
- Test: `apps/api/tests/test_page_text_extractor.py`
- Test: `apps/api/tests/test_text_manifest_store.py`
- Update: `reports/final/results/text_manifest_quality.md`

**Implementation target:**
- Extract text, blocks, words, page dimensions, and quality stats.
- Persist and reload manifests per paper.
- Preserve the current lightweight caption path in ingestion/indexing so page evidence cards still show text before full manifest consumers are wired.
- Mark weak pages with `ocr_needed` instead of inventing text evidence.

**Acceptance checks:**
- Born-digital PDF pages produce text and word/block metadata.
- Empty or low-text pages are marked low quality.
- Manifest reload is deterministic.
- Page numbers and rendered page images still align.
- Current caption-based vector payload tests continue to pass or are updated to assert the caption fallback explicitly.

**Report contribution:** Text quality and OCR limitation subsection.

**Demo contribution:** Text snippet evidence can be displayed beside page image evidence.

**Exit gate:** Each indexed paper can produce a text manifest with quality flags.

### Node 4: BM25 Text Retriever

**Objective:** Add a cheap, explainable lexical retrieval channel.

**Files:**
- Create: `apps/api/app/services/text_retriever.py`
- Test: `apps/api/tests/test_text_retriever.py`
- Update: `eval/retrieval/run_retrieval_eval.py`
- Update: `reports/final/results/bm25_metrics.md`

**Implementation target:**
- Build page-level BM25 documents from persisted manifests, not from transient vector captions alone.
- Return page-level text hits with best snippets and source ranks.
- Keep BM25 scores separate from visual scores.

**Acceptance checks:**
- Exact method, dataset, abbreviation, and citation-token queries retrieve expected pages.
- BM25 can run without external model calls.
- Eval script can produce a BM25-only baseline row.

**Report contribution:** BM25 baseline row and text retrieval discussion.

**Demo contribution:** Show one case where text retrieval finds a method/dataset term.

**Exit gate:** BM25-only retrieval is measurable and does not replace VisRAG.

### Node 5: Page-Canonical Hybrid Retrieval

**Objective:** Fuse BM25 and VisRAG into validated EvidencePackets.

**Files:**
- Create: `apps/api/app/services/evidence_resolver.py`
- Create: `apps/api/app/services/hybrid_retrieval_service.py`
- Modify: `apps/api/app/routers/retrieval.py`
- Modify: `apps/api/app/services/chat_service.py` if chat should consume hybrid retrieval in the same node
- Test: `apps/api/tests/test_hybrid_retrieval_service.py`
- Update: `eval/retrieval/run_retrieval_eval.py`
- Update: `reports/final/results/hybrid_metrics.md`

**Implementation target:**
- Run BM25 and VisRAG for the same scoped request.
- Aggregate BM25 spans by page.
- Apply RRF at `(paper_id, page_number)`.
- Preserve source scores/ranks and provenance.
- Wrap current `VectorStore.search_pages()` results into packet units instead of bypassing existing scoped search behavior.

**Acceptance checks:**
- Hybrid packets include page image plus best text snippets when available.
- Text-only, visual-only, and hybrid queries all work with mocked retrievers.
- Retrieval never leaks outside selected `paper_ids`.
- Eval script can produce a hybrid row.
- Existing `/retrieval/search` behavior remains available, or any packet-aware response extension is additive and documented.

**Report contribution:** Main technical comparison table.

**Demo contribution:** Show the EvidencePacket with both text and visual evidence.

**Exit gate:** Hybrid retrieval improves or clearly complements at least one baseline case.

### Node 6: Verified Chat And Evidence UI

**Objective:** Make the product visibly useful before adding multi-pass autonomy.

**Files:**
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/context_builder.py`
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/use-chat-session.ts`
- Modify: `apps/web/components/evidence-panel.tsx`
- Modify: `apps/web/components/chat-panel.tsx`
- Test: `apps/api/tests/test_chat_prompt.py`
- Test: `apps/api/tests/test_chat_streaming.py`
- Test: `apps/api/tests/test_public_evidence_response.py`
- Update: `demo/shot-list.md`

**Implementation target:**
- Chat consumes a verified `EvidencePacket`.
- Prompt context uses stable evidence IDs.
- Preserve existing SSE streaming order: early evidence frame, token deltas, final done frame.
- UI displays answer, evidence, limits, source modality, and page links/thumbnails using the existing evidence panel and citation-chip behavior.

**Acceptance checks:**
- Chat citations are limited to accepted evidence.
- Weak or missing evidence produces a visible limit/refusal.
- Public API response is path-redacted.
- `npm --prefix apps/web run typecheck` passes.
- Existing streaming chat tests continue to pass.

**Report contribution:** System screenshot and user-facing trust mechanism.

**Demo contribution:** First recordable product walkthrough.

**Exit gate:** A user can ask one scoped question and see answer + evidence + limits.

### Node 7: Three-Pass Bounded Research Orchestrator

**Objective:** Upgrade the existing bounded query planner into the agentic autonomy required by the rubric.

**Files:**
- Create: `apps/api/app/services/research_orchestrator.py`
- Create: `apps/api/app/schemas/agent_trace.py`
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/context_builder.py`
- Modify: `apps/api/app/schemas/chat.py`
- Test: `apps/api/tests/test_research_orchestrator.py`
- Test: `apps/api/tests/test_chat_service_agentic.py`
- Update: `reports/final/results/agent_trace_examples.md`
- Update: `demo/shot-list.md`

**Implementation target:**
- Implement `QueryRewrite`, `FirstRetrieval`, `EvidenceAnalysis`, `SecondRetrieval`, `SufficiencyCheck`, `FinalRetrieval`, `Answer`.
- Reuse the current `enable_agentic_retrieval` entry point and bounded planner prompt as the compatibility bridge.
- Require JSON-only planner decisions and validate them as untrusted hints.
- Enforce max passes, max query variants, max final evidence units, and evidence delta checks.

**Acceptance checks:**
- Illegal planner actions are rejected.
- The loop terminates within three passes.
- A no-new-evidence second pass triggers sufficiency/refusal.
- Trace-safe actions are returned without hidden reasoning.
- Existing single-step planner fallback behavior remains covered as a regression case.

**Report contribution:** Agent autonomy figure and trace table.

**Demo contribution:** Show planning, first retrieval, evidence gap, second retrieval, final answer/refusal.

**Exit gate:** The system is demonstrably more than a simple chat/RAG interface.

### Node 8: Robustness And Safety Package

**Objective:** Prove commercial trust boundaries.

**Files:**
- Create: `eval/robustness/`
- Create: `apps/api/tests/test_prompt_injection_pdf.py`
- Create: `apps/api/tests/test_retrieval_robustness.py`
- Update: `reports/final/results/robustness_matrix.md`
- Update: `reports/final/results/failure_gallery.md`

**Implementation target:**
- Add deterministic fixtures for empty scope, missing evidence, conflicting evidence, low-text pages, prompt-injection PDF text, and citation drift.
- Record how the system limits, refuses, or marks `need_verification`.

**Acceptance checks:**
- Prompt-injection text inside PDFs cannot change system/tool rules.
- Empty and missing evidence cases do not produce confident paper-grounded claims.
- Conflicting evidence is surfaced as a limit or verification need.
- Robustness matrix is report-ready.

**Report contribution:** Trust and robustness section.

**Demo contribution:** One short refusal or malicious-PDF safety clip.

**Exit gate:** The system has visible failure behavior, not only happy-path behavior.

### Node 9: Commercial Stress Test And Cost Panel

**Objective:** Turn system traces into profit logic.

**Files:**
- Create: `reports/final/results/cost_benefit.csv`
- Create: `reports/final/results/cost_benefit.md`
- Create: `scripts/estimate_run_cost.py`
- Update: `demo/shot-list.md`

**Implementation target:**
- Estimate per-run input/output tokens or provider cost from actual traces where available.
- Refresh market pricing and wage references immediately before report freeze.
- Compute three scenarios: 20-PDF evidence packet, 50-PDF consulting/R&D landscape, and systematic-review pre-screening.

**Acceptance checks:**
- Cost model includes AI/API/compute cost, human verification time, and fully loaded hourly labor assumption.
- Report table includes assumptions and sensitivity range.
- Claims stay bounded to first-pass evidence gathering and citation packaging.

**Report contribution:** Profit Logic and Commercial Stress Test.

**Demo contribution:** ROI/cost slide or UI panel for the road-show close.

**Exit gate:** The business value can be explained numerically in under 20 seconds.

### Node 10: Final Report Package

**Objective:** Produce the graded written artifact.

**Files:**
- Create: `reports/final/main.tex`
- Create: `reports/final/references.bib`
- Create: `reports/final/figures/`
- Create: `reports/final/tables/`
- Create: `reports/final/appendix/`
- Create: `reports/final/checklist.md`

**Implementation target:**
- Write the paper in NeurIPS 2025 style.
- Include problem verification, related work/competitors, architecture, methods, baseline comparison, trust/robustness, cost-benefit, reproducibility, and conclusion.
- Keep main body at or under nine pages, with references and appendices after.

**Acceptance checks:**
- Report compiles to a single PDF.
- Main body page limit is checked.
- Every major claim points to either system output, eval result, cost table, or citation.
- NeurIPS checklist is answered honestly.

**Report contribution:** Final deliverable.

**Demo contribution:** Provides the investor/reader narrative for the video.

**Exit gate:** The report PDF is ready for review, not just a draft.

### Node 11: Three-Minute Demo Video Package

**Objective:** Produce the road-show deliverable.

**Files:**
- Create: `demo/script.md`
- Create: `demo/shot-list.md`
- Create: `demo/recording-checklist.md`
- Create: `demo/assets/`
- Optional create: `demo/final-video-notes.md`

**Implementation target:**
- Script a 3-minute story: problem, agent plan, evidence packet, bounded retrieval repair, refusal/safety, ROI.
- Prepare deterministic local run commands and backup screenshots/clips.
- Keep the demo focused on the commercial buyer: saved analyst/researcher time and trustworthy citations.

**Acceptance checks:**
- Script reads in 170-190 seconds at normal pace.
- Shot list maps every spoken claim to a screen moment.
- Demo shows at least one multi-paper answer, one evidence packet with page evidence, one bounded follow-up retrieval, and one refusal or limit.
- Recording checklist includes local server, seeded corpus, provider keys/model setting, browser zoom, and fallback assets.

**Report contribution:** Road-show evidence and appendix pointer.

**Demo contribution:** Final deliverable.

**Exit gate:** A recorder can make the 3-minute video from the package without inventing new content.

## Phase 0: Baseline Evaluation And Report Evidence

**Purpose:** Create report-ready evidence before retrieval changes are judged by anecdotes.

- [ ] Build a 20-30 item golden set if time allows; the minimum demo-safe version is 10-15 cases.
- [ ] Include 20-30% negative or failure cases: no evidence, conflicting evidence, misleading similar pages, and visual-required questions.
- [ ] Use fixture fields: `question`, `paper_ids`, `expected_pages`, `answer_key`, `must_cite_pages`, `should_refuse`, `question_type`.
- [ ] Record current VisRAG baseline: Recall@1, Recall@3, Recall@5, MRR or nDCG if cheap, citation-page correctness, and refusal correctness.
- [ ] Add scripts that emit JSON plus report-ready CSV/Markdown.

**Verification:** One local command regenerates baseline metrics without contacting an external model provider.

## Phase 1: EvidenceUnit v0 And Validators

**Purpose:** Make evidence trustworthy before improving retrieval or adding agent behavior.

- [ ] Define `EvidenceUnit` and `EvidencePacket` schemas.
- [ ] Generate deterministic `evidence_id` from paper/page/source/span-or-page hash.
- [ ] Validate paper/page existence, image existence, citation IDs, source labels, selected `paper_ids`, and local-path redaction.
- [ ] Add unsupported-claim guardrails: generated answers may only cite accepted evidence IDs.
- [ ] Keep bbox/crop/OCR fields nullable.

**Verification:** Tests prove invalid paper/page references fail, citations cannot point outside the evidence set, and public responses do not expose local filesystem paths.

## Phase 2: PyMuPDF Text Manifest

**Purpose:** Add the first reliable text evidence path without blocking on OCR.

- [ ] Extract page text, blocks, and words with PyMuPDF.
- [ ] Store page width/height and coordinate metadata so future crops can map text back to PNG pages.
- [ ] Compute `text_quality`: character count, word count, printable ratio, repeated-character ratio, block count, word count, empty-page flag, and `ocr_needed`.
- [ ] Mark low-quality/scanned pages as visual-first instead of pretending text evidence exists.
- [ ] Record the PyMuPDF/MuPDF AGPL/commercial-license issue as a commercial deployment risk.

**Verification:** Tests cover born-digital PDFs, empty pages, low-text pages, low-quality text, manifest reload, and page/image alignment.

## Phase 3: BM25 Text Retrieval

**Purpose:** Add a lightweight local text channel for exact scientific terms, method names, datasets, variables, abbreviations, and citation tokens.

- [ ] Define `TextRetriever`.
- [ ] Implement `BM25TextRetriever` over page-level manifest documents.
- [ ] Return best page-level hits with optional best snippets/spans.
- [ ] Keep raw BM25 scores, rank, and source metadata, but do not compare raw BM25 scores with vector similarity.
- [ ] Defer dense text embeddings until after BM25 + VisRAG hybrid is measurable.

**Verification:** Tests show exact method names, dataset names, abbreviations, and citation tokens are retrievable even when visual retrieval is mocked.

## Phase 4: Page-Canonical Hybrid Retrieval

**Purpose:** Combine text and visual retrieval into a single auditable evidence packet.

- [ ] Run existing VisRAG page search and BM25 text search for the same scoped request.
- [ ] Collapse BM25 text spans to `(paper_id, page_number)` before fusion.
- [ ] Apply Reciprocal Rank Fusion by source rank.
- [ ] Preserve `bm25_score`, `visrag_score`, `source_rank`, `rrf_score`, and modality/source provenance for debugging.
- [ ] Resolve every accepted page to both page image and best available text snippets.
- [ ] Enforce paper scope so retrieval never leaks across selected `paper_ids`.

**Verification:** Tests prove text-only, visual-only, and hybrid queries produce stable packets, preserve provenance, dedupe pages correctly, and respect paper scope.

## Phase 5: Verified Chat Integration

**Purpose:** Improve answer quality before introducing multi-step orchestration.

- [ ] Update `ChatService` to retrieve one verified `EvidencePacket`.
- [ ] Update `context_builder.py` to render compact, citation-stable packet context.
- [ ] Preserve ordinary conversation mode when no paper scope is selected.
- [ ] Preserve visible `Answer`, `Evidence`, and `Limits` sections.
- [ ] Add explicit insufficient-evidence behavior when scoped retrieval finds no validated evidence.

**Verification:** Tests prove chat receives packet evidence, citations are limited to packet units, and weak evidence produces limits/refusal rather than confident claims.

## Phase 6: Three-Pass Bounded Research Orchestrator

**Purpose:** Demonstrate agentic autonomy while keeping behavior testable and commercially safe.

- [ ] Implement the fixed state machine.
- [ ] Require JSON-only planner outputs and strict schema validation.
- [ ] Execute all retrieval, fusion, dedupe, validation, and clamping server-side.
- [ ] Record pass count, query changes, evidence delta count, refusal reason, and budget usage.
- [ ] Add prompt-injection fixtures where PDF text attempts to override system behavior.
- [ ] Expose trace-safe actions and evidence; hide private reasoning.

**Verification:** Mock-tool tests prove illegal planner actions are rejected, state order cannot be skipped, weak evidence refuses or limits claims, and the loop terminates.

## Phase 7: Commercial Report, Road Show, And Robustness Package

**Purpose:** Convert the engineering system into a high-scoring final submission.

- [ ] Build baseline comparison: manual/GPT-only/current VisRAG/hybrid EvidencePacket/bounded agent.
- [ ] Report metrics: Recall@k, citation-page accuracy, evidence coverage, unsupported claims, refusal correctness, latency, and cost per run.
- [ ] Build cost-benefit calculator:
  - `net_savings = (manual_hours - PaperMemory_hours - verification_hours) * fully_loaded_hourly_rate - API_or_compute_cost - license_cost`
- [ ] Use three commercial scenarios: 20-PDF evidence packet, 50-PDF consulting/R&D landscape, and systematic-review pre-screening with explicit non-replacement language.
- [ ] Prepare road-show demo: upload PDFs, ask a multi-paper question, show evidence planning, show evidence packet, click citation/page evidence, show insufficient-evidence refusal, compare against baseline, show cost panel.
- [ ] Add robustness matrix: private PDFs, scanned PDFs, prompt-injection PDF text, conflicting evidence, missing evidence, long documents, and citation drift.
- [ ] Prepare appendix: eval set, raw outputs, prompts/schemas, setup commands, hyperparameters, cost calculations, and NeurIPS checklist answers.

**Verification:** The report contains empirical results, reproducible artifacts, a cost-benefit table, reliability/safety cases, and a road-show video script aligned with the rubric.

## Baselines For The Final Report

- GPT-only over user question.
- Current single-pass VisRAG page retrieval.
- BM25-only text retrieval after Phase 3.
- Hybrid BM25 + VisRAG EvidencePacket after Phase 4.
- Bounded evidence agent after Phase 6.

The strongest claim should be comparative and bounded: the system improves evidence coverage and citation reliability for private multi-PDF research tasks, not that it performs unconstrained literature review.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Branch drift after baseline selection | Baseline is `origin/miles` commit `6884d738df9d685bad4f5a673a7d13a7bc2fb691`; check for new drift before each implementation node |
| Evidence alignment drift | Validate paper/page/image/text manifest links before answer generation |
| Page-vs-span granularity mismatch | Fuse at page level first; attach best spans inside each page |
| BM25 noisy text from PDF layout | Store `text_quality`; down-rank or mark visual-first pages |
| Scanned PDFs | Mark `ocr_needed`; treat OCR as future extension |
| Prompt injection inside PDFs | Treat PDF text as untrusted evidence; require structured outputs and server-side tool execution |
| Prompt theater | Require measurable evidence deltas and state-machine validation |
| Overfit eval | Call the first set a golden regression set; expand before making benchmark claims |
| PyMuPDF license | Record AGPL/commercial-license decision for commercialization |

## Reference Anchors

- [VisRAG](https://arxiv.org/abs/2410.10594) and [openbmb/VisRAG-Ret](https://huggingface.co/openbmb/VisRAG-Ret) support page-image document retrieval.
- [PyMuPDF text extraction](https://pymupdf.readthedocs.io/en/latest/recipes-text.html), [blocks/words extraction](https://pymupdf.readthedocs.io/en/latest/app1.html), and [OCR notes](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html) support the manifest path and `ocr_needed` flag.
- [Qdrant hybrid search](https://qdrant.tech/course/essentials/day-3/hybrid-search/), [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/), [RRF SIGIR 2009](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf), and [Elasticsearch RRF](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) support rank-level fusion.
- [ReAct](https://arxiv.org/abs/2210.03629), [FLARE](https://arxiv.org/abs/2305.06983), and [Self-RAG](https://arxiv.org/abs/2310.11511) support iterative retrieve/inspect/retrieve patterns; PaperMemory should describe itself as inspired by these, not as reimplementing their training methods.
- [PaperQA2](https://arxiv.org/abs/2409.13740), [OpenScholar](https://arxiv.org/abs/2411.14199), [RAGAS](https://arxiv.org/abs/2309.15217), [ALCE](https://github.com/princeton-nlp/ALCE), and [AIS](https://aclanthology.org/2023.cl-4.2/) support citation-grounded evaluation design.
- [Elicit pricing](https://elicit.com/pricing), [Consensus plans](https://help.consensus.app/en/articles/10087865-subscription-plans), and BLS wage pages for [management analysts](https://www.bls.gov/ooh/business-and-financial/management-analysts.htm), [medical scientists](https://www.bls.gov/ooh/life-physical-and-social-science/medical-scientists.htm), and [data scientists](https://www.bls.gov/ooh/math/data-scientists.htm) support market and cost-benefit framing. Refresh all pricing before the final report.
