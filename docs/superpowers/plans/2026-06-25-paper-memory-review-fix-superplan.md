# PaperMemory Review Fix Superplan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PaperMemory implementation and evidence artifacts ready for a later assignment report and three-minute demo, without producing or polishing the final report/demo in this pass.

**Architecture:** Use a readiness-first pass. Repair the evidence contract, retrieval visibility, bounded orchestrator, and robustness metadata so future report/demo work can truthfully cite real behavior; keep report/demo checks as acceptance constraints rather than current deliverables.

**Tech Stack:** FastAPI/Pydantic services, pytest, Next.js/TypeScript typecheck, LaTeX/Tectonic report package, Markdown durable planning files.

---

## Source Context

- Original source plan: `docs/superpowers/plans/2026-06-22-paper-memory-evidence-agent.md`
- Completed-node durable memory: `.planning/2026-06-22-paper-memory-evidence-agent/`
- Review basis: node-by-node subagent audit plus cross-node delivery audit run on 2026-06-25.
- Current baseline remains `origin/miles` / `HEAD` commit `6884d738df9d685bad4f5a673a7d13a7bc2fb691` unless a new fetch changes it before execution.
- Main delivery objective: a future truthful written report and recorder-ready three-minute demo. This pass prepares the implementation evidence those artifacts will later use.

## Readiness-First Recalibration

The previous delivery-first recalibration was too artifact-oriented: it made the current pass look responsible for finishing the report and demo package. The user clarified that this work should prepare the system so those artifacts can be created later. Therefore, the current pass should fix implementation and evidence-readiness gaps while treating report/demo needs as downstream constraints.

Use this revised priority order:

1. **Readiness scope audit:** confirm which review findings must be fixed now to enable future report/demo claims, and which artifact-polish tasks should remain deferred.
2. **Evidence-contract foundation:** repair public EvidencePacket validation, path redaction, and file-backed validation first.
3. **Visible evidence behavior:** fix source labels, weak-evidence limits, bounded image attachment, safe orchestrator failure behavior, low-text metadata, and trace sanitization.
4. **Report/demo readiness notes:** only record the evidence boundaries, future comparison rows, and deterministic demo recipe requirements needed by the later report/demo pass; do not write the final report/demo content now.
5. **Readiness verification:** run focused backend/frontend checks that prove the future report/demo can rely on these behaviors.

Stop when the implementation substrate is ready enough for the later report/demo pass. Do not treat existing `reports/final/` or `demo/` artifacts as final deliverables for this pass.

## Stage-Gated Execution Correction

The user clarified on 2026-06-26 that each original Node is a stage indicator, not a standing instruction to execute all downstream work in one run. When a stage is reached, first write or refresh a stage-specific plan, then start subagents against that stage plan.

Use this execution model:

1. Treat Node 0-11 from the original plan as stage gates for the assignment story.
2. Before implementing any node/stage, create or update a stage plan with objective, file scope, report/demo evidence contribution, tests, non-goals, and handoff notes.
3. Only after that stage plan is recorded, dispatch bounded subagents for implementation or review.
4. After subagents finish, the main controller runs spec review, code quality review, local verification, and durable status updates.
5. Do not auto-advance to the next stage. Decide the next stage only after the current stage is reviewed against the report/demo objective.

Current correction after Task 5 acceptance: the next action is a stage-decision pause, not automatic Task 6 execution. Task 6 remains a future demo-readiness template unless the user explicitly chooses that stage. Do not write a Task 6 stage plan, launch subagents, or edit demo readiness files merely because Task 5 finished.

Tasks 5-6 below are future-input/readiness stage templates for report/demo creation. They are not instructions to produce the final report, final demo, or a continuous all-nodes run.

## Acceptance Gate

The immediate code-readiness pass is complete only when all of these are true:

- Public EvidencePackets do not expose path-like diagnostics in `limits`, including empty packets.
- Public retrieval/chat packet validation distinguishes structural validation from file-backed validation and does not mark missing page assets as validated.
- Evidence UI labels single-source hybrid candidates as `BM25 text` or `VisRAG-Ret`, reserving `Hybrid` for candidates with both traces.
- Weak evidence receives a deterministic visible limit instead of relying only on prompt wording.
- Chat image attachment is server-clamped to at most three evidence images.
- Bounded orchestrator retrieval/validation failures degrade to trace-safe partial results.
- Low-text/OCR-needed quality metadata reaches real EvidenceUnits through the retrieval path.
- Trace/planner sanitization redacts `API keys`, `credentials`, `tokens`, and related plural forms.

Deferred report/demo-readiness gates, to be planned when those stages are reached:

- Readiness notes identify which later report comparison rows are measured, qualitative, or N/A.
- Readiness notes identify the deterministic demo corpus/question/provider requirements the later demo pass should use.

## File Map

### Evidence Contract And Retrieval Validation

- Modify: `apps/api/app/services/evidence_validator.py`
- Modify: `apps/api/app/routers/retrieval.py`
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/hybrid_retrieval_service.py`
- Test: `apps/api/tests/test_evidence_contract.py`
- Test: `apps/api/tests/test_public_evidence_response.py`

### Evidence Visibility And Weak Limits

- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/web/components/evidence-panel.tsx`
- Optional create: `apps/web/lib/evidence-labels.ts`
- Test: `apps/api/tests/test_chat_service_agentic.py`
- Verify: `npm --prefix apps/web run typecheck`

### Bounded Orchestrator Safety

- Modify: `apps/api/app/schemas/chat.py`
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/research_orchestrator.py`
- Test: `apps/api/tests/test_chat_service_agentic.py`
- Test: `apps/api/tests/test_research_orchestrator.py`

### Robustness Metadata And Trace Sanitization

- Modify: `apps/api/app/schemas/retrieval.py`
- Modify: `apps/api/app/services/text_retriever.py`
- Modify: `apps/api/app/services/evidence_resolver.py`
- Modify: `apps/api/app/schemas/agent_trace.py`
- Modify: `apps/api/app/services/research_orchestrator.py`
- Test: `apps/api/tests/test_hybrid_retrieval_service.py`
- Test: `apps/api/tests/test_prompt_injection_pdf.py`
- Test: `apps/api/tests/test_retrieval_robustness.py`

### Readiness Notes And Planning

- Modify or create: `reports/final/results/comparison_matrix.md` only as a future-report input artifact.
- Modify or create: `demo/readiness-notes.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/task_plan.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/progress.md`

## Execution Rules

- Preserve the original Node 0-11 implementation intent; do not expand claims to real-corpus performance, OCR robustness, dense semantic retrieval, comprehensive security, or systematic-review replacement.
- Treat future report and demo needs as constraints, not current deliverables.
- Do not auto-execute across tasks. Each task/node is a stage gate; when it becomes current, write or refresh a stage-specific plan before starting subagents.
- After each accepted task, pause for a stage decision. The phrase "next stage" means "next candidate if explicitly chosen", not permission to continue automatically.
- Treat Task 6 as a deferred demo-readiness template. It should not start until the user chooses a demo-readiness stage and a fresh Task 6 stage plan is recorded.
- Do not edit `reports/final/main.tex`, report tables, demo script, shot list, or recording checklist in this pass unless a tiny note is needed to prevent future confusion.
- Use one task slice at a time. After each implementation slice, run the listed focused checks and update `.planning/2026-06-25-paper-memory-review-fix-superplan/progress.md`.
- Use subagents for implementation when possible, with disjoint write scopes. Main controller must verify locally before marking a task complete.
- Do not commit or stage unless the user explicitly requests it.
- If a review finding is only about final wording, defer it to the later report/demo pass and record the boundary in `findings.md`.

---

## Task 0: Readiness Scope Audit

**Files:**
- Read: `docs/superpowers/plans/2026-06-22-paper-memory-evidence-agent.md`
- Read: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
- Read: `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`
- Read: `reports/final/results/*.md` when needed as future-report inputs.
- Read: `demo/*.md` when needed as future-demo inputs.

- [ ] **Step 1: Classify each review finding by readiness role**

Use this classification:

- `fix-now`: blocks a future report/demo claim because current behavior is wrong or unsafe.
- `note-for-later`: only affects final report/demo wording or packaging.
- `defer`: nice-to-have engineering cleanup outside the assignment evidence path.

Expected: Tasks 1-4 findings are `fix-now`; final report/demo wording issues are `note-for-later`.

- [ ] **Step 2: Confirm the next implementation slice**

Record in `progress.md`:

- next task: Task 1 EvidencePacket validation boundary
- reason: public evidence boundary is foundational for every later report/demo claim
- non-goal: no final report/demo content edits in this slice

- [ ] **Step 3: Keep future artifact issues visible but deferred**

Add a short `note-for-later` list in `findings.md` for:

- final comparison rows/N.A. rationale
- stale report/demo wording
- locked demo recipe details
- final PDF/demo timing checks

Expected: these notes are not executed until the later report/demo creation pass.

## Task 1: Repair EvidencePacket Validation Boundary

**Files:**
- Modify: `apps/api/app/services/evidence_validator.py`
- Modify: `apps/api/app/routers/retrieval.py`
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/hybrid_retrieval_service.py`
- Test: `apps/api/tests/test_evidence_contract.py`
- Test: `apps/api/tests/test_public_evidence_response.py`

- [ ] **Step 1: Add failing tests for empty-packet limit redaction**

Add a test equivalent to:

```python
def test_validate_evidence_packet_rejects_path_like_limits_without_units() -> None:
    packet = EvidencePacket(
        packet_id="ep-empty-limit-leak",
        query=None,
        paper_scope=[],
        units=[],
        citations=[],
        limits=[r"C:\secret\paper.pdf"],
    )

    with pytest.raises(EvidenceValidationError, match="limits"):
        validate_evidence_packet(packet)
```

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_contract.py::test_validate_evidence_packet_rejects_path_like_limits_without_units -q
```

Expected before fix: fail because the packet validates. Expected after fix: pass.

- [ ] **Step 2: Make `limits` redaction unconditional**

In `apps/api/app/services/evidence_validator.py`, remove the `if packet.units or packet.citations` guard and always call:

```python
_assert_no_public_path("evidence packet limits", packet.limits)
```

Keep user query text out of this check; only packet public fields and packet limits are checked.

- [ ] **Step 3: Add file-backed validation tests for public packet paths**

Add one route-level test that uses a temporary `Settings(storage_root=tmp_path / "storage")`, a fake vector store returning `PageEvidence(paper_id="missing-paper", page_number=999, score=0.9)`, and asserts the route does not return a packet whose unit is marked `validated`.

Accepted outcomes:

- HTTP `500`/`422` with safe error detail, or
- HTTP `200` with packet units not marked `validated` plus an explicit limit.

Do not accept HTTP `200` with `validation_state="validated"` for the missing page image case.

- [ ] **Step 4: Thread storage-aware validation through public retrieval/chat**

Use `StoragePaths(settings)` in `apps/api/app/routers/retrieval.py` for the visual branch. For `ChatService`, add an optional `storage_paths` constructor argument and route it from `apps/api/app/routers/chat.py`.

Implement one internal helper in `ChatService`:

```python
def _validate_packet_for_public_response(
    self,
    packet: EvidencePacket,
    *,
    paper_scope: list[str] | None,
    require_files: bool = False,
) -> EvidencePacket:
    return validate_evidence_packet(
        packet,
        paths=self.storage_paths,
        paper_scope=paper_scope,
        require_files=bool(require_files and self.storage_paths is not None),
    )
```

Use this helper for public chat packets. Keep unit tests that construct `ChatService` without paths working by defaulting `storage_paths=None`.

- [ ] **Step 5: Run focused verification**

```powershell
python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_public_evidence_response.py -q
python -m pytest apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_service_agentic.py -q
```

Expected: all selected tests pass.

## Task 2: Fix Evidence Visibility Labels And Weak-Evidence Limits

**Files:**
- Modify: `apps/web/components/evidence-panel.tsx`
- Optional create: `apps/web/lib/evidence-labels.ts`
- Modify: `apps/api/app/services/chat_service.py`
- Test: `apps/api/tests/test_chat_service_agentic.py`

- [ ] **Step 1: Correct hybrid source labeling**

Change the label rule so `Hybrid` requires both visual and text traces:

```typescript
const retrievers = new Set(unit.rank_trace.map((trace) => trace.retriever.toLowerCase()));
const hasVisual = retrievers.has("visrag") || unit.source === "visrag_page";
const hasText = retrievers.has("bm25") || unit.source === "text_page";

if (hasVisual && hasText) return "Hybrid";
if (hasText) return "BM25 text";
return "VisRAG-Ret";
```

If this helper remains in `evidence-panel.tsx`, keep it small. If extracting it improves typecheck clarity, create `apps/web/lib/evidence-labels.ts` and import it from the component.

- [ ] **Step 2: Add deterministic weak-evidence limit**

Add a clear limit string in `apps/api/app/services/chat_service.py`:

```python
WEAK_EVIDENCE_LIMIT = (
    "Accepted evidence is low confidence; verify cited pages before relying on the answer."
)
```

Add a helper that flags weak scores only when the packet has no stronger evidence:

```python
@staticmethod
def _has_only_weak_scores(packet: EvidencePacket) -> bool:
    scored = [unit.score for unit in packet.units if unit.score is not None]
    return bool(scored) and all(score < 0.40 for score in scored)
```

Then append `WEAK_EVIDENCE_LIMIT` in `_packet_quality_limits()` when `_has_only_weak_scores(packet)` is true.

This preserves hybrid RRF honesty: if all accepted units are low-scored, the UI shows a visible trust boundary rather than a hidden prompt-only warning.

- [ ] **Step 3: Add API regression for weak limit**

Add a test using a packet with one or more `EvidenceUnit(score=0.03, source="hybrid_page")` and assert the final `ChatResponse.limits` and `evidence_packet.limits` contain `WEAK_EVIDENCE_LIMIT`.

Run:

```powershell
python -m pytest apps/api/tests/test_chat_service_agentic.py -q
npm --prefix apps/web run typecheck
```

Expected: pytest passes and TypeScript typecheck passes.

## Task 3: Enforce Bounded Orchestrator Safety

**Files:**
- Modify: `apps/api/app/schemas/chat.py`
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/research_orchestrator.py`
- Test: `apps/api/tests/test_chat_service_agentic.py`
- Test: `apps/api/tests/test_research_orchestrator.py`

- [ ] **Step 1: Clamp evidence images to three server-side**

Add a constant:

```python
MAX_ATTACHED_EVIDENCE_IMAGES = 3
```

Clamp at the service boundary before calling `ModelGateway.build_user_content()`:

```python
max_images = request.max_evidence_images
if max_images is not None:
    max_images = min(max_images, MAX_ATTACHED_EVIDENCE_IMAGES)
```

Pass `max_images`, not the raw request value. Lowering `ChatRequest.max_evidence_images` from `le=10` to `le=3` is allowed only if existing UI/API callers do not rely on the wider schema.

- [ ] **Step 2: Add clamp regression**

Use a fake gateway that records `max_evidence_images`. Send `ChatRequest(max_evidence_images=10, enable_image_context=True)` and assert the gateway receives `3`.

Run:

```powershell
python -m pytest apps/api/tests/test_chat_service_agentic.py::test_chat_service_clamps_evidence_images_to_three -q
```

Expected before fix: fail with raw `10`. Expected after fix: pass with `3`.

- [ ] **Step 3: Make orchestrator retrieval failures trace-safe**

In `ResearchOrchestrator._run_retrieval_pass()`, catch retrieval and packet validation failures per query. Append a public action like:

```python
AgentTraceAction(
    state=state,
    pass_index=pass_index,
    query=query,
    retrieval_mode="hybrid",
    evidence_delta_count=0,
    note="retrieval pass failed; bounded partial result returned",
)
```

Merge a limit such as:

```python
"Retrieval pass failed; returning bounded partial evidence instead of continuing unbounded."
```

Then continue to the next query or return `0` delta. Do not expose exception text because it may contain local paths or provider details.

- [ ] **Step 4: Add orchestrator failure regressions**

Add tests for:

- `retrieval.search()` raising `RuntimeError("boom C:\\secret")`
- `retrieval.search()` returning an object with malformed or invalid `evidence_packet`

Assert:

- `orchestrator.run()` returns an `OrchestratorResult`
- final stop reason is `insufficient_evidence`, `no_new_evidence`, or `budget_exhausted`
- public trace and limits do not contain local paths or raw exception text

Run:

```powershell
python -m pytest apps/api/tests/test_research_orchestrator.py -q
```

Expected: all orchestrator tests pass.

## Task 4: Propagate Low-Text Metadata And Harden Trace Sanitization

**Files:**
- Modify: `apps/api/app/schemas/retrieval.py`
- Modify: `apps/api/app/services/text_retriever.py`
- Modify: `apps/api/app/services/evidence_resolver.py`
- Modify: `apps/api/app/schemas/agent_trace.py`
- Modify: `apps/api/app/services/research_orchestrator.py`
- Test: `apps/api/tests/test_hybrid_retrieval_service.py`
- Test: `apps/api/tests/test_prompt_injection_pdf.py`
- Test: `apps/api/tests/test_retrieval_robustness.py`

- [ ] **Step 1: Allow safe quality metadata in public evidence**

Extend `PUBLIC_METADATA_KEYS` in `apps/api/app/schemas/retrieval.py`:

```python
PUBLIC_METADATA_KEYS = {
    "embedding_model",
    "embedding_instruction",
    "quality_label",
    "text_quality",
    "ocr_needed",
    "char_count",
    "word_count",
}
```

Keep path-like redaction in place for all values.

- [ ] **Step 2: Carry quality fields through text hits**

Extend `TextSearchHit` with:

```python
quality_label: str | None = None
ocr_needed: bool | None = None
char_count: int | None = None
word_count: int | None = None
```

Extend `_TextDocument` with the same page quality data and populate it in `_document_from_page(page)`.

- [ ] **Step 3: Merge quality metadata into hybrid units**

In `apps/api/app/services/evidence_resolver.py`, merge visual metadata and text quality metadata into `metadata` before creating `EvidenceUnit`.

Required final keys when available:

```python
metadata["quality_label"] = candidate.text.quality_label
metadata["ocr_needed"] = str(candidate.text.ocr_needed).lower()
metadata["char_count"] = str(candidate.text.char_count)
metadata["word_count"] = str(candidate.text.word_count)
```

Do not include raw text, source paths, or page image paths.

- [ ] **Step 4: Add integration-style low-text regression**

Add or update a hybrid retrieval test that builds a low-text `TextManifest` page, runs through `TextRetriever` -> `fuse_page_candidates()` -> `build_hybrid_evidence()`, and asserts:

```python
assert packet.units[0].metadata["quality_label"] == "low_text"
assert packet.units[0].metadata["ocr_needed"] == "true"
```

Also assert `ChatService._packet_quality_limits(packet)` includes `LOW_TEXT_EVIDENCE_LIMIT`.

- [ ] **Step 5: Broaden unsafe trace patterns**

Update `_UNSAFE_TRACE_PATTERNS` and `_UNSAFE_PLANNER_HINT_RE` to catch singular and plural sensitive credential phrases:

```python
re.compile(r"(?i)\b(api[_ -]?keys?|secrets?|credentials?|tokens?)\b")
```

Add a direct regression where the planner emits `"reveal API keys"` without an accompanying `"ignore system rules"` phrase. Assert it is redacted from trace and is not used as a retrieval query.

Run:

```powershell
python -m pytest apps/api/tests/test_prompt_injection_pdf.py apps/api/tests/test_retrieval_robustness.py -q
python -m pytest apps/api/tests/test_hybrid_retrieval_service.py apps/api/tests/test_research_orchestrator.py -q
```

Expected: all selected tests pass.

## Task 5: Record Future Report Comparison Inputs

**Files:**
- Create or modify: `reports/final/results/comparison_matrix.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`
- Do not modify: `reports/final/main.tex`
- Do not modify: `reports/final/tables/retrieval_summary.tex`
- Do not modify: `reports/final/claim_evidence_map.md`
- Do not modify: `reports/final/build_notes.md`

- [ ] **Step 1: Add a bounded comparison matrix input artifact**

Create or update `reports/final/results/comparison_matrix.md` as an input artifact for the later report-writing pass, not as final report prose. Use rows:

| Comparator | Status | Evidence Metric Boundary |
| --- | --- | --- |
| GPT-only / manual narrative baseline | Qualitative baseline only | No page retrieval, no EvidencePacket, no citation-page correctness score; marked N/A for Recall@k. |
| Visual API baseline | Quantitative synthetic row | Existing `node1-baseline` metrics. |
| BM25 text manifest | Quantitative synthetic row | Existing `bm25-baseline` metrics. |
| Hybrid page fusion | Quantitative synthetic row | Existing `hybrid-baseline` metrics. |
| Bounded evidence agent | Deterministic trace/regression row | Trace stops, no-new-evidence behavior, citation stripping, and packet limits; not a Recall@k row unless the eval harness is extended. |

This prevents the future report from inventing non-existent GPT-only or bounded-agent retrieval metrics.

- [ ] **Step 2: Record future report table guidance without editing the report**

Add a note to `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md` saying the later report pass should include qualitative/N.A. rows or a companion table. Keep percentage metrics only where measured.

Example row wording:

```tex
GPT-only/manual narrative & N/A & N/A & N/A & N/A & N/A & No page retrieval or EvidencePacket; qualitative baseline only. \\
Bounded evidence agent & Trace & Trace & Trace & Packet-only & Packet-only & Deterministic state-machine tests; not a retrieval benchmark row. \\
```

- [ ] **Step 3: Record future claim-map guidance without editing final prose**

Add a `note-for-later` entry in `findings.md` for:

- GPT-only/manual baseline is qualitative/N.A.
- Bounded agent is evaluated by trace/regression, not Recall@k.
- Later report text around the retrieval table should say the table combines measured synthetic retrieval rows and explicit N/A comparator rows.

- [ ] **Step 4: Verify no final-report prose was changed**

```powershell
git diff -- reports/final/main.tex reports/final/tables/retrieval_summary.tex reports/final/claim_evidence_map.md reports/final/build_notes.md
```

Expected: no diff for final report prose/table/build-note files in this readiness pass.

## Task 6: Record Future Demo Readiness Recipe

**Files:**
- Create or modify: `demo/readiness-notes.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`
- Do not modify: `demo/recording-checklist.md`
- Do not modify: `demo/shot-list.md`
- Do not modify: `demo/local-run.md`
- Do not modify: `demo/final-video-notes.md`

- [ ] **Step 1: Record the intended locked live recipe**

Create or update `demo/readiness-notes.md` with:

```markdown
## Locked Live Demo Recipe

- Library: `demo-library-paper-memory`
- Group: `group-core-demo`
- Papers: `demo-visrag-core`, `demo-bm25-text`
- Primary question: "Compare the current retrieval substrate and planned exact-term baseline: which pages describe VisRAG page-image search and future BM25 exact matching?"
- Refusal question: "What evidence supports mitochondrial ribosome profiling in this corpus?"
- Expected primary evidence: `demo-visrag-core p.1` and `demo-bm25-text p.1`
- Expected refusal behavior: no accepted citations and a visible missing-evidence or partial-answer limit.
```

If those synthetic papers are not loaded in the live app, say explicitly:

```markdown
If the locked synthetic corpus is not loaded, record the static fallback assets only and do not present the live UI as the deterministic run.
```

- [ ] **Step 2: Record provider/model setting requirements**

Use the environment names already visible in the app/API docs when available. If exact project env names are not present, use the request/API fields as the stable contract:

```markdown
- Provider path: OpenAI-compatible / BYOK.
- Required request fields or UI settings: `base_url`, `model`, `api_key`.
- No-key fallback: record `chat_ui_packet.md`, `agent_trace_examples.md`, and `failure_gallery.md`; do not fake a model response.
```

Before execution, check `.env.example`, `README.md`, and app settings UI files for exact variable names. Use exact env names if they exist.

- [ ] **Step 3: Record future shot-list guidance without editing the shot list**

Add to `demo/readiness-notes.md`: the later demo pass should replace generic “Ask a scoped hybrid question” language with the locked primary question and expected evidence pages.

- [ ] **Step 4: Record historical-run cleanup as a later packaging item**

Add to `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md` that the later demo pass should distinguish:

- Node 0 historical typecheck result, and
- current post-fix typecheck result after `npm --prefix apps/web run typecheck`.

Do not edit `demo/local-run.md` during the readiness pass unless the user explicitly starts the demo packaging node.

## Task 7: Final Cross-Node Verification And Durable Status Update

**Files:**
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/task_plan.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/progress.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`
- Optional modify: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`

- [ ] **Step 1: Run focused backend verification**

```powershell
python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_public_evidence_response.py -q
python -m pytest apps/api/tests/test_chat_prompt.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_service_agentic.py -q
python -m pytest apps/api/tests/test_research_orchestrator.py apps/api/tests/test_prompt_injection_pdf.py apps/api/tests/test_retrieval_robustness.py -q
python -m pytest apps/api/tests/test_hybrid_retrieval_service.py apps/api/tests/test_text_retriever.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run frontend and readiness-note verification**

```powershell
npm --prefix apps/web run typecheck
python -c "from pathlib import Path; paths=['reports/final/results/comparison_matrix.md','demo/readiness-notes.md']; [print(p, Path(p).exists(), Path(p).stat().st_size if Path(p).exists() else 0) for p in paths]"
git diff --check
```

Expected: typecheck passes, readiness input files exist if Tasks 5-6 ran, and diff check has no errors beyond known CRLF warnings.

- [ ] **Step 3: Update durable planning state**

Record:

- exact tests run and results in `progress.md`
- any new technical decisions in `findings.md`
- task status changes in `task_plan.md`

If every task passes, optionally update the original `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md` to say the post-review fix pass is complete. Do not change the original historical Node statuses unless the user asks for history rewriting.

## Self-Review Checklist

- Spec coverage: every Important review finding has a task above.
- Placeholder scan: this plan contains no open placeholder markers.
- Claim boundary: all report/demo changes preserve synthetic/local evidence boundaries.
- Test coverage: every code-risk task has at least one focused pytest/typecheck command.
- Execution mode: recommended execution is subagent-driven, one task slice at a time, with main-controller verification after each slice.
