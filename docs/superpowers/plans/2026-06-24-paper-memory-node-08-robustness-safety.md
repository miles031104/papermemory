# PaperMemory Node 8 Robustness And Safety Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic robustness and safety evidence showing PaperMemory refuses, limits, or safely traces weak, missing, conflicting, low-text, and prompt-injection evidence cases.

**Architecture:** Node 8 builds on Node 7's bounded orchestrator and Node 6's packet-visible chat without changing the product architecture. It adds focused fixtures and tests for trust boundaries, then exports a report-ready robustness matrix and failure gallery. The implementation should prove existing guardrails and add small missing guardrails only where tests expose a concrete gap.

**Tech Stack:** Python 3.12, pytest, FastAPI TestClient, existing `EvidencePacket`, `ResearchOrchestrator`, `ChatService`, local synthetic fixtures.

---

## Stage Boundary

Node 8 is a robustness and safety package. It must not implement Node 9 cost modeling, Node 10 final report writing, Node 11 video production, OCR, dense text embeddings, new retrieval algorithms, a frontend redesign, or broad product UI work. It may add small backend guardrails only when a deterministic safety test demonstrates the need.

## Current Baseline Findings

- Remote baseline was refreshed before planning. `HEAD`, `origin/miles`, and merge-base are all `6884d738df9d685bad4f5a673a7d13a7bc2fb691`.
- Node 7 is complete: scoped hybrid chat can use a server-verified bounded orchestrator with sanitized trace actions, planner JSON validation, evidence-delta stops, and final packet validation.
- Existing tests already cover path redaction, empty/no-scope packet behavior, citation containment, invalid planner JSON, extra planner fields, sanitized planner query execution, and no-new-evidence stops.
- Node 8 should broaden the deterministic trust cases rather than reimplementing the orchestrator.

## File Map

- Create: `eval/robustness/fixtures.py`
  - Shared synthetic packets, evidence units, fake retrieval/planner helpers, and case descriptors.
- Create: `eval/robustness/README.md`
  - Documents the deterministic robustness cases and their report boundaries.
- Create: `apps/api/tests/test_prompt_injection_pdf.py`
  - Tests untrusted PDF text/captions cannot change planner/system/tool behavior or leak into trace.
- Create: `apps/api/tests/test_retrieval_robustness.py`
  - Tests missing evidence, empty scope, conflicting evidence, low-text/scanned markers, no-new-evidence, and citation drift behavior.
- Modify if required by failing tests: `apps/api/app/services/context_builder.py`
  - Keep PDF text untrusted wording in prompts.
- Modify if required by failing tests: `apps/api/app/services/research_orchestrator.py`
  - Add small guardrail notes/limits only if tests expose a real gap.
- Modify if required by failing tests: `apps/api/app/services/chat_service.py`
  - Ensure weak/missing/conflicting evidence produces bounded answer limits.
- Update: `reports/final/results/robustness_matrix.md`
  - Case-by-case PASS/FAIL/SCOPE table.
- Update: `reports/final/results/failure_gallery.md`
  - Short examples of safe failures and limits.
- Update: `demo/shot-list.md`
  - Add one short Node 8 refusal/safety demo beat.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - Record commands, review outcomes, and boundaries.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
  - Move Node 8 through `stage_plan_ready`, `in_progress`, and review statuses.

## Robustness Cases

Node 8 should cover these deterministic cases:

1. **Empty scope:** no selected papers or no ready papers must not produce paper-grounded claims.
2. **Missing evidence:** scoped retrieval returns no accepted units; answer should be partial/limited and cite nothing.
3. **No-new-evidence loop:** Node 7 second pass repeats the same accepted page; trace stops with `no_new_evidence`.
4. **Prompt-injection PDF text:** caption/snippet asks the model to ignore system rules, reveal secrets, execute tools, or change citations; public trace and planner prompt must treat it as untrusted evidence.
5. **Citation drift:** generated answer cites pages outside the accepted packet; citation verifier strips or rejects those citations.
6. **Conflicting evidence:** two accepted pages support incompatible values; final prompt/limits must surface uncertainty or verification need instead of forcing a confident claim.
7. **Low-text/scanned marker:** text manifest quality indicates weak/no text or `ocr_needed`; system should mark visual-first/limit rather than invent text evidence.

## Task Plan

### Task 1: Robustness Fixture Helpers

**Files:**
- Create: `eval/robustness/fixtures.py`
- Create: `eval/robustness/README.md`

- [ ] Add helpers to build `EvidenceUnit`, `EvidencePacket`, `HybridRetrievalResult`, and `OrchestratorResult` objects with deterministic IDs.
- [ ] Add fake retrieval and fake planner helpers that record calls and support repeated/no-new-evidence scenarios.
- [ ] Add case descriptors for empty scope, missing evidence, prompt injection, citation drift, conflicting evidence, and low-text/scanned markers.
- [ ] Write README boundary text: these are deterministic safety/regression cases, not a real-world scanned-PDF OCR benchmark.

### Task 2: Prompt Injection And Trace Safety Tests

**Files:**
- Create: `apps/api/tests/test_prompt_injection_pdf.py`
- Modify if required: `apps/api/app/services/context_builder.py`
- Modify if required: `apps/api/app/services/research_orchestrator.py`

- [ ] Test prompt-injection captions are included only as evidence in prompts and cannot change allowed JSON keys or tool rules.
- [ ] Test planner decisions containing extra action fields or local path strings stop safely or are sanitized before retrieval.
- [ ] Test public `AgentTrace` JSON does not contain path-like strings, API-key wording, hidden reasoning labels, `<think>` tags, or raw prompt-injection instructions.
- [ ] Run:

```powershell
python -m pytest apps/api/tests/test_prompt_injection_pdf.py -q
```

Expected after implementation: pass.

### Task 3: Retrieval Robustness Tests

**Files:**
- Create: `apps/api/tests/test_retrieval_robustness.py`
- Modify if required: `apps/api/app/services/chat_service.py`
- Modify if required: `apps/api/app/services/research_orchestrator.py`

- [ ] Test empty scope and missing evidence produce no paper-grounded citations.
- [ ] Test no-new-evidence second pass stops with `no_new_evidence`.
- [ ] Test citation drift outside accepted packet pages is stripped.
- [ ] Test conflicting evidence is surfaced as a limit or verification-needed note.
- [ ] Test low-text/scanned markers produce an explicit limit such as OCR/future-work or visual-first evidence rather than fabricated text evidence.
- [ ] Run:

```powershell
python -m pytest apps/api/tests/test_retrieval_robustness.py -q
```

Expected after implementation: pass.

### Task 4: Report And Demo Robustness Artifacts

**Files:**
- Create: `reports/final/results/robustness_matrix.md`
- Create: `reports/final/results/failure_gallery.md`
- Modify: `demo/shot-list.md`
- Modify: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
- Modify: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`

- [ ] Write a matrix with rows for each robustness case, expected behavior, command/test evidence, and claim boundary.
- [ ] Write a short failure gallery with examples of safe refusal, no-new-evidence stop, citation stripping, and prompt-injection trace redaction.
- [ ] Add one demo beat showing a refusal or visible limit rather than a confident unsupported answer.
- [ ] Keep wording bounded: Node 8 demonstrates deterministic trust behavior, not comprehensive security proof or OCR robustness.

### Task 5: Required Verification

**Files:** no direct code edits.

- [ ] Run focused robustness tests:

```powershell
python -m pytest apps/api/tests/test_prompt_injection_pdf.py apps/api/tests/test_retrieval_robustness.py -q
```

- [ ] Run existing safety/packet/orchestrator regressions:

```powershell
python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_research_orchestrator.py apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_public_evidence_response.py -q
```

- [ ] Run hybrid service regression:

```powershell
python -m pytest apps/api/tests/test_hybrid_retrieval_service.py -q
```

- [ ] Run frontend typecheck if API response types or web-facing fields change:

```powershell
npm --prefix apps/web run typecheck
```

- [ ] Run diff hygiene:

```powershell
git diff --check
```

## Subagent Plan

### Subagent A: Node 8 Robustness Implementer

**Role:** worker.

**Write scope:** files listed in File Map.

**Task:** Implement deterministic robustness fixtures, tests, minimal guardrails needed by failing tests, and report/demo artifacts. Do not implement cost modeling, final report/video, OCR, dense embeddings, or frontend redesign.

### Subagent B: Node 8 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Verify implementation matches this stage plan:

- Empty/missing evidence cases do not produce paper-grounded claims.
- Prompt-injection text is treated as untrusted evidence and cannot alter tool/system behavior.
- Trace output remains public-safe.
- Citation drift is stripped or rejected.
- Conflicting/low-text cases surface limits rather than fabricated certainty.
- Robustness matrix and failure gallery are report-ready and claim-bounded.
- Node 9-11 work is not implemented prematurely.

### Subagent C: Node 8 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability and claim boundaries:

- Fixtures are deterministic and reusable without becoming a parallel app.
- Tests focus on observable trust behavior rather than brittle prompt strings.
- Guardrails are small and localized.
- Report/demo wording avoids overclaiming comprehensive security, OCR, or systematic-review coverage.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 8:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 8 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 8 Gate

Node 8 is accepted only when:

- All required commands pass.
- Spec review passes.
- Quality review passes.
- Robustness matrix and failure gallery exist.
- Demo shot list includes one refusal/safety beat.
- The next stage remains Node 9: Commercial Stress Test And Cost Panel.
