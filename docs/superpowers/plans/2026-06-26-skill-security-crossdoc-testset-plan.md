# Skill Security Cross-Document Testset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a five-question report/demo test set from three agent-skill security papers that evaluates PaperMemory's cross-document retrieval, reasoning, and safety behavior.

**Architecture:** Use the three PDFs as a controlled corpus. The test set is stored as a human-readable report artifact plus a machine-readable JSON artifact. Future execution should run the questions in PaperMemory and compare answers against page-anchored expected elements.

**Tech Stack:** Markdown, JSON, PaperMemory API/UI, hybrid retrieval, agentic `/chat` trace, local PDF text extraction with PyMuPDF.

---

### Task 1: Confirm Corpus And Shut Down Existing Services

**Files:**
- Read: `C:\Users\Miles CUI\Desktop\文档\荣誉论文\skills paper\skill inject.pdf`
- Read: `C:\Users\Miles CUI\Desktop\文档\荣誉论文\skills paper\malicous agent skill.pdf`
- Read: `C:\Users\Miles CUI\Desktop\文档\荣誉论文\skills paper\trojan whisper.pdf`
- Modify: `.planning/2026-06-26-skill-security-crossdoc-testset/progress.md`

- [x] Stop old PaperMemory services on ports `8000` and `3000`.
- [x] Verify `http://127.0.0.1:8000/health` and `http://127.0.0.1:3000` do not respond.
- [x] Confirm all three PDFs exist and record file sizes.

### Task 2: Extract Paper Anchors

**Files:**
- Modify: `.planning/2026-06-26-skill-security-crossdoc-testset/findings.md`

- [x] Extract page counts and first-page/abstract text with PyMuPDF.
- [x] Search for anchor facts: benchmark size, attack success rates, malicious-skill counts, taxonomy labels, evasion rates, and defense recommendations.
- [x] Record page-level anchors that future PaperMemory answers should cite.

### Task 3: Create The Five-Question Test Set

**Files:**
- Create: `reports/final/results/skill_security_crossdoc_testset.md`
- Create: `eval/skill_security_crossdoc_testset.json`

- [x] Write exactly five questions.
- [x] For each question, include capability target, required source papers, expected answer elements, evidence anchors, scoring rubric, and failure modes.
- [x] Keep the wording suitable for a live demo and final report.

### Task 4: Save Durable Planning State

**Files:**
- Create: `.planning/2026-06-26-skill-security-crossdoc-testset/task_plan.md`
- Create: `.planning/2026-06-26-skill-security-crossdoc-testset/findings.md`
- Create: `.planning/2026-06-26-skill-security-crossdoc-testset/progress.md`
- Modify: `.planning/.active_plan`

- [x] Link the durable task plan to this source plan.
- [x] Record service shutdown evidence and PDF extraction findings.
- [x] Set this plan as active.

### Task 5: Future Execution Gate

**Files:**
- Output: `artifacts/skill-security-crossdoc-testset/2026-06-27/`

- [x] Start PaperMemory only when the user asks to run this set.
- [x] Upload the three PDFs into a clean group without duplicate pollution.
- [x] Run all five questions and save redacted results.
- [x] Score each answer against the test set rubric.
- [x] Promote only evidence-backed results into the final report/demo.

Result: execution gate passed, answer-quality gate partial. The automatic scorecard is a heuristic baseline; use `artifacts/skill-security-crossdoc-testset/2026-06-27/manual-quality-review.md` and `reports/final/results/skill_security_crossdoc_live_results.md` as the report-facing interpretation. Q2 and Q5 are not report-ready success cases.
