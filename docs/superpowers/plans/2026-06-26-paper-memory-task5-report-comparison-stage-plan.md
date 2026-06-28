# PaperMemory Task 5 Report Comparison Inputs Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a bounded comparison-matrix input artifact for the later final-report pass, without editing final report prose, tables, build notes, or claim maps.

**Architecture:** Treat this as report-readiness data curation, not report writing. Use existing result artifacts under `reports/final/results/` to classify comparator rows as measured, qualitative, trace/regression, or N/A. Protect final report files with SHA-256 checks because these files are currently untracked and `git diff` alone cannot prove they were not changed.

**Tech Stack:** Markdown result artifacts, PowerShell hash checks, durable planning files.

---

## Stage Boundary

This is a stage plan for Task 5 from `docs/superpowers/plans/2026-06-25-paper-memory-review-fix-superplan.md`.

Do not edit:

- `reports/final/main.tex`
- `reports/final/tables/retrieval_summary.tex`
- `reports/final/claim_evidence_map.md`
- `reports/final/build_notes.md`
- any `demo/` file

Allowed edits:

- Create: `reports/final/results/comparison_matrix.md`
- Modify: `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`

Do not stage or commit.

## Evidence Sources To Read

- `reports/final/results/baseline_metrics.md`
- `reports/final/results/bm25_metrics.md`
- `reports/final/results/hybrid_metrics.md`
- `reports/final/results/agent_trace_examples.md`
- `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`

Current facts from inspected artifacts:

- `node1-baseline`: synthetic smoke corpus, 4 synthetic papers, 12 synthetic pages, Recall@1 77.8%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%; not real-PDF/real-VisRAG/real-local-corpus benchmark.
- `bm25-baseline`: synthetic BM25-only text manifest, Recall@1 88.9%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 100.0%; not real-PDF/real-corpus/hybrid/RRF/VisRAG benchmark.
- `hybrid-baseline`: synthetic hybrid fixture baseline, Recall@1 77.8%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%, both-trace units 27; not real-PDF/real-corpus improvement benchmark.
- `agent_trace_examples.md`: bounded evidence agent contribution is trace/regression behavior: accepted evidence IDs, per-pass evidence deltas, stop reasons, validated final packets; not exhaustive literature-review coverage or a Recall@k benchmark.

## Task 5A: Protect Final Report Files

- [ ] **Step 1: Capture protected-file hashes before editing**

Run:

```powershell
Get-FileHash `
  reports/final/main.tex, `
  reports/final/tables/retrieval_summary.tex, `
  reports/final/claim_evidence_map.md, `
  reports/final/build_notes.md `
  -Algorithm SHA256 | Format-Table Path,Hash -AutoSize
```

Record the four hashes in your final report back to the controller. Do not write them into final report files.

## Task 5B: Create Comparison Matrix Input Artifact

- [ ] **Step 2: Create `reports/final/results/comparison_matrix.md`**

Create this exact artifact shape, preserving the boundary language:

```markdown
# Comparison Matrix Input Artifact

This file is an input for a later final-report writing pass. It is not final report prose and should not be cited as a real-corpus benchmark.

## Comparator Boundaries

| Comparator | Status | Evidence Metric Boundary | Existing Evidence Source |
| --- | --- | --- | --- |
| GPT-only / manual narrative baseline | Qualitative baseline only | N/A for Recall@k, citation-page correctness, and retrieval-level refusal correctness because no page retriever or EvidencePacket is executed. Use only as a narrative contrast row unless a separate executable baseline is added. | No measured row exists. |
| Visual API baseline | Quantitative synthetic row | Synthetic smoke corpus only: Recall@1 77.8%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%. Not a real-PDF, real-VisRAG, or real-local-corpus benchmark. | `reports/final/results/baseline_metrics.md` (`node1-baseline`) |
| BM25 text manifest | Quantitative synthetic row | Synthetic text-manifest corpus only: Recall@1 88.9%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 100.0%. Not a real-PDF, real-corpus, hybrid, RRF, or VisRAG benchmark. | `reports/final/results/bm25_metrics.md` (`bm25-baseline`) |
| Hybrid page fusion | Quantitative synthetic row | Synthetic hybrid fixture baseline only: Recall@1 77.8%, Recall@3 100.0%, Recall@5 100.0%, citation-page correctness 100.0%, refusal correctness 33.3%, both-trace units 27. Not a real-PDF or real-corpus improvement benchmark. | `reports/final/results/hybrid_metrics.md` (`hybrid-baseline`) |
| Bounded evidence agent | Deterministic trace/regression row | Trace stops, no-new-evidence behavior, citation stripping, packet limits, accepted evidence IDs, evidence deltas, stop reasons, and validated final packets. Not a Recall@k row unless the eval harness is extended to score agent retrieval outputs. | `reports/final/results/agent_trace_examples.md` plus backend regression tests |

## Future Report Table Guidance

- Keep percentage metrics only on measured synthetic retrieval rows.
- Represent GPT-only/manual narrative as qualitative or N/A, not as a hidden zero or invented retrieval score.
- Represent the bounded evidence agent as a trace/regression comparator, not as a retrieval benchmark row.
- If the later report combines these rows in one table, use a companion `Metric type` or `Boundary` column so measured retrieval metrics and N/A comparator rows are visibly different.
- Do not describe any row here as real local-corpus, real-PDF, real-VisRAG quality, systematic-review completeness, OCR robustness, or dense semantic retrieval performance.
```

Do not add metrics not present in the inspected source artifacts.

## Task 5C: Record Durable Later-Report Guidance

- [ ] **Step 3: Append a note to findings**

Append this section to `.planning/2026-06-25-paper-memory-review-fix-superplan/findings.md`:

```markdown
## 2026-06-26 Task 5 Report Comparison Input Findings

- Created `reports/final/results/comparison_matrix.md` as a later-report input artifact, not final report prose.
- Future report guidance:
  - GPT-only/manual narrative is qualitative/N/A unless an executable same-corpus baseline is added.
  - Bounded evidence agent is trace/regression evidence, not a Recall@k retrieval benchmark row.
  - Percentage metrics should remain limited to measured synthetic retrieval rows: `node1-baseline`, `bm25-baseline`, and `hybrid-baseline`.
  - Later report text around the retrieval table should say it combines measured synthetic retrieval rows and explicit qualitative/N/A comparator rows.
- Claim boundary: this artifact does not create real-corpus, real-PDF, real-VisRAG, OCR robustness, dense semantic retrieval, or systematic-review completeness claims.
```

## Task 5D: Verify No Final Report Prose Was Changed

- [ ] **Step 4: Compare protected-file hashes after editing**

Run the same hash command from Step 1:

```powershell
Get-FileHash `
  reports/final/main.tex, `
  reports/final/tables/retrieval_summary.tex, `
  reports/final/claim_evidence_map.md, `
  reports/final/build_notes.md `
  -Algorithm SHA256 | Format-Table Path,Hash -AutoSize
```

The four hashes must match the Step 1 hashes exactly.

- [ ] **Step 5: Run file-existence and content checks**

Run:

```powershell
python -c "from pathlib import Path; p=Path('reports/final/results/comparison_matrix.md'); text=p.read_text(encoding='utf-8'); required=['GPT-only / manual narrative baseline','N/A for Recall@k','node1-baseline','bm25-baseline','hybrid-baseline','Trace stops','not final report prose']; print(p.exists(), p.stat().st_size); missing=[s for s in required if s not in text]; print('missing=', missing); raise SystemExit(1 if missing else 0)"
```

Expected: file exists, non-zero size, `missing=[]`.

- [ ] **Step 6: Run diff hygiene**

Run:

```powershell
git diff --check -- reports/final/results/comparison_matrix.md .planning/2026-06-25-paper-memory-review-fix-superplan/findings.md
```

Expected: exit `0`; CRLF warnings are acceptable only if there are no whitespace errors.

## Handoff Notes For Subagents

- Implementer must not modify final report prose/table/build-note files.
- Spec reviewer must verify the matrix does not invent measured GPT-only or bounded-agent Recall@k metrics.
- Code quality reviewer must verify the artifact is useful for later report writing while preserving claim boundaries.
- Main controller must independently check protected-file hashes before marking Task 5 complete.

## Self-Review

- Spec coverage: this plan covers comparison matrix creation, findings note, protected-file verification, no final report edits, and claim-boundary constraints.
- Placeholder scan: no placeholder steps remain.
- Type/path consistency: all paths match the current repo structure under `reports/final/` and `.planning/2026-06-25-paper-memory-review-fix-superplan/`.
