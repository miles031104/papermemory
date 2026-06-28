# PaperMemory Node 1 Golden Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible Node 1 measurement spine for the current PaperMemory `/retrieval/search` baseline before changing retrieval behavior.

**Architecture:** Node 1 is a stage objective, not a single implementation prompt. The stage first defines a local golden fixture and a deterministic retrieval-eval runner, then uses subagents to reconcile implementation artifacts against this plan, followed by spec and quality review. The runner must exercise the latest-code retrieval API surface without modifying API, service, or web production code.

**Tech Stack:** Python 3.12, FastAPI `TestClient`, current `PageEvidence` and `VectorStore` interfaces, JSONL fixtures, JSON/CSV/Markdown result exports.

---

## Stage Boundary

The source superplan defines Node 1 as "Demo Corpus And Golden Evaluation Harness." For this checkout, `storage/papers/` has no real local PDFs, so Node 1 must not claim real-corpus retrieval quality. It may create a deterministic synthetic smoke corpus that validates the eval harness, current route contract, required fixture fields, and report/demo measurement outputs.

Existing Node 1 files, if present before this plan is executed, are candidate implementation artifacts only. They are not accepted until an implementation subagent reconciles them against this stage plan and both review gates pass.

## File Map

- Create or reconcile: `eval/retrieval/golden_questions.jsonl`
  - Owns the 10-15 row golden fixture.
  - Each row must include required fields and current scope metadata.
- Create or reconcile: `eval/retrieval/run_retrieval_eval.py`
  - Owns CLI parsing, fixture validation, synthetic corpus construction, calls into the current FastAPI `/retrieval/search` route, metric aggregation, and output writing.
- Create or reconcile: `eval/retrieval/results/README.md`
  - Documents output files, rerun command, and interpretation boundary.
- Generate or refresh: `eval/retrieval/results/node1-baseline.json`
  - Full run payload.
- Generate or refresh: `eval/retrieval/results/node1-baseline.csv`
  - Spreadsheet-friendly per-question summary.
- Generate or refresh: `eval/retrieval/results/node1-baseline.md`
  - Reader-facing result summary.
- Create or reconcile: `reports/final/results/baseline_metrics.md`
  - Report-ready methods/evaluation setup table and first baseline row.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - Append commands, results, concerns, and review outcomes.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
  - Node 1 status only after plan-based implementation and review gates.

Do not modify production files under `apps/api`, `apps/web`, `package.json`, or `package-lock.json` in Node 1.

## Acceptance Contract

- Fixture has 10-15 questions.
- Refusal or negative rows are 20-30% of the fixture.
- Every fixture row includes:
  - `question`
  - `paper_ids`
  - `expected_pages`
  - `answer_key`
  - `must_cite_pages`
  - `should_refuse`
  - `question_type`
- Every fixture row includes current Paper Manager scope provenance:
  - `library_id`
  - `group_id`
  - `provenance`
- The fixture includes at least one primary multi-paper question.
- The fixture includes at least one refusal or missing-evidence question.
- The runner can be rerun from the repo root with:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
```

- The runner writes JSON, CSV, and Markdown outputs under `eval/retrieval/results/`.
- Metrics include:
  - Recall@1
  - Recall@3
  - Recall@5
  - citation-page correctness
  - refusal correctness
- The runner calls the current FastAPI `POST /retrieval/search` route through `TestClient` and dependency overrides.
- The synthetic path uses current `PageEvidence` response fields and current `VectorStore` page search semantics where practical.
- All report/result files clearly state that synthetic mode is not a real-PDF, real-VisRAG, or real-local-corpus benchmark.

## Subagent Plan

### Subagent A: Node 1 Implementation Reconciler

**Role:** worker.

**Write scope:** only the files listed in the File Map.

**Task:** Reconcile any existing candidate Node 1 artifacts with this stage plan. If artifacts already satisfy the plan, make only necessary status/documentation corrections. If they do not, patch them until the acceptance contract is met.

- [ ] Check whether candidate Node 1 files already exist.
- [ ] Validate `golden_questions.jsonl` row count, required fields, scope fields, negative share, multi-paper question, and refusal question.
- [ ] Validate that `run_retrieval_eval.py` has a deterministic synthetic mode and calls `/retrieval/search` through `TestClient`.
- [ ] Run the Node 1 baseline command:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode synthetic --output-prefix node1-baseline
```

- [ ] Validate generated JSON:

```powershell
python -m json.tool eval/retrieval/results/node1-baseline.json
```

- [ ] Run API regression smoke:

```powershell
python -m pytest apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_public_evidence_response.py -q
```

- [ ] Update `reports/final/results/baseline_metrics.md` with the latest generated metrics and limitations.
- [ ] Append the exact commands and outcomes to `progress.md`.
- [ ] Set Node 1 status in `task_plan.md` to `complete_with_synthetic_corpus` only if all acceptance checks and command checks pass. Otherwise set `in_progress` or `blocked` with a precise concern.

### Subagent B: Node 1 Spec Reviewer

**Role:** default or explorer.

**Write scope:** none.

**Task:** Review implementation against this stage plan and the source superplan's Node 1 acceptance checks.

- [ ] Confirm no production API/web/package files changed.
- [ ] Confirm all required fixture fields and scope metadata exist.
- [ ] Confirm the synthetic boundary is explicit in result and report files.
- [ ] Confirm outputs include JSON, CSV, Markdown, and report metrics.
- [ ] Confirm metrics include all required Node 1 metrics.
- [ ] Confirm command evidence is recorded in `progress.md`.

### Subagent C: Node 1 Quality Reviewer

**Role:** default or explorer.

**Write scope:** none.

**Task:** Review maintainability and claim boundaries.

- [ ] Check that the runner is deterministic and small enough for a stage harness.
- [ ] Check that metrics are computed at page grain and do not overclaim answer-level quality.
- [ ] Check that refusal correctness is labeled retrieval-level if it only measures no-evidence retrieval.
- [ ] Check that fixture content does not pretend planned BM25/EvidencePacket features already exist in production.
- [ ] Check that result files are reproducible from the documented command.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 1:

1. Round 1: implementation reconciler, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 1 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 1 Gate

Node 1 is accepted only when:

- Implementation is reconciled to this stage plan.
- Spec review passes.
- Quality review passes.
- Required commands are recorded.
- `task_plan.md` status matches the true boundary.
- The next stage is still Node 2: EvidenceUnit and EvidencePacket Contract.
