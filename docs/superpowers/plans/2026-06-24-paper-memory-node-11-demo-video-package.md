# PaperMemory Node 11 Three-Minute Demo Video Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a complete road-show demo package that lets a recorder create a three-minute PaperMemory video without inventing new claims, screens, or backup material.

**Architecture:** Node 11 is the final demo packaging stage. It turns the Node 6-10 UI/report artifacts into a timed script, shot map, recording checklist, fallback asset manifest, and final video notes. It must not implement new product behavior or actually require video recording inside this environment.

**Tech Stack:** Markdown demo artifacts, existing app/run documentation, existing report PDF and results artifacts, optional static fallback assets such as rendered PDF pages or screenshots generated from already-created artifacts.

---

## Stage Boundary

Node 11 may create and update demo planning assets only. It must not change backend/frontend product code, retrieval logic, evaluation code, report claims, pricing models, OCR, dense embeddings, billing UI, or any Node 0-10 result values. It may generate static fallback images from existing artifacts if helpful for recording, but it should not claim that a final video file has been recorded unless a real video is produced.

## Current Baseline Findings

- Remote baseline was refreshed before planning. `HEAD`, `origin/miles`, and merge-base are all `6884d738df9d685bad4f5a673a7d13a7bc2fb691`.
- Node 10 is complete: `reports/final/main.pdf` exists, compiles to 8 pages, and passed spec plus paper-quality reviews.
- Existing `demo/shot-list.md` already includes Node 6 verified chat/UI, Node 7 bounded orchestrator, Node 8 robustness/safety, and Node 9 commercial stress-test segments.
- Existing `demo/local-run.md` records the intended local baseline flow and notes that frontend dependency install/typecheck should be restored before treating the web recording path as clean.

## File Map

- Create: `demo/script.md`
  - Timed 170-190 second narration with screen cues and claim boundaries.
- Update: `demo/shot-list.md`
  - Consolidate existing node segments into one final 3-minute shot sequence.
- Create: `demo/recording-checklist.md`
  - Local server, seeded corpus, provider key/model settings, browser zoom, recording settings, and fallback plan.
- Create: `demo/assets/`
  - Optional static backup assets or asset manifest.
- Optional create: `demo/final-video-notes.md`
  - Recording status, final-video handoff notes, or explicit “not recorded yet” status.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`

## Demo Story

The script must cover this 3-minute arc:

1. Problem: PDF literature work fails when retrieval, citations, and uncertainty are not visible.
2. Agent plan: PaperMemory runs a bounded, server-verified evidence loop over selected papers.
3. Evidence packet: the UI/API exposes accepted page evidence, citations, modality, limits, and page links.
4. Bounded retrieval repair: the trace shows a second pass or a `no_new_evidence` stop rather than unbounded agent behavior.
5. Refusal/safety: missing, conflicting, low-text, or prompt-injection-like evidence produces visible limits instead of confident unsupported claims.
6. ROI close: cost-benefit table frames first-pass evidence gathering and citation packaging with human verification, not guaranteed ROI.

## Required Screen Moments

The final shot list must map every spoken claim to a visible moment:

- Multi-paper or multi-page answer.
- Evidence packet with accepted citations and page evidence.
- Page/evidence click or evidence panel provenance.
- Public bounded trace with pass index, evidence delta, stop reason, or accepted evidence ids.
- Refusal, partial answer, missing evidence, low-text/conflict limit, or citation stripping.
- Cost/ROI table or report page from `reports/final/results/cost_benefit.md` or `reports/final/main.pdf`.
- Final report PDF or title page as closing proof of package completeness.

If live UI recording is not possible, the shot list must define fallback static assets from existing report/results files.

## Timing Requirements

- `demo/script.md` must read in 170-190 seconds at normal pace.
- Use approximately 390-500 spoken English words, or an equivalent timed line estimate.
- Include timestamps or duration blocks for each scene.
- Avoid visible/in-app instructional text; the script should narrate the screen, not describe internal implementation details that are not visible.

## Claim Boundaries

The demo may claim:

- PaperMemory makes page-level evidence, citations, limits, and traces visible.
- The current package demonstrates deterministic behavior on local synthetic fixtures and regression tests.
- The cost table is a planning stress test for first-pass evidence gathering.
- Human verification remains required.

The demo must not claim:

- Real-corpus performance.
- Systematic-review replacement.
- Comprehensive security or prompt-injection immunity.
- OCR robustness.
- Dense semantic retrieval.
- Guaranteed ROI or validated customer demand.
- Feature parity with Elicit, Consensus, or any commercial product.

## Task Plan

### Task 1: Final Script

**Files:**
- Create: `demo/script.md`

- [ ] Write a timed 170-190 second script with scene labels.
- [ ] Include word count and estimated read time.
- [ ] Keep every claim supported by Node 6-10 artifacts.
- [ ] Include explicit non-replacement and human-verification language.

### Task 2: Final Shot List

**Files:**
- Update: `demo/shot-list.md`

- [ ] Add a final 3-minute recording sequence that stitches the Node 6-9 segments into one coherent video.
- [ ] Map each script segment to concrete screen moments and fallback assets.
- [ ] Ensure the required screen moments are all covered.
- [ ] Preserve existing node boundary notes.

### Task 3: Recording Checklist And Assets

**Files:**
- Create: `demo/recording-checklist.md`
- Create: `demo/assets/`
- Optional create: `demo/final-video-notes.md`

- [ ] Include local server startup commands and ports.
- [ ] Include seeded corpus / synthetic fixture / report asset preparation.
- [ ] Include provider key/model settings and a no-key fallback path.
- [ ] Include browser zoom, window size, recording resolution, audio, and backup capture notes.
- [ ] Include fallback assets from existing artifacts, such as report PDF pages, cost table, robustness matrix, or static screenshots.
- [ ] If no video is recorded, explicitly state that the package is recorder-ready, not final-video-complete.

### Task 4: Verification

**Files:** no direct code edits.

- [ ] Check script duration:

```powershell
python -c "from pathlib import Path; import re; text=Path('demo/script.md').read_text(encoding='utf-8'); words=re.findall(r\"[A-Za-z0-9']+\", text); print(len(words)); assert 390 <= len(words) <= 500"
```

- [ ] Check required terms/screen moments:

```powershell
rg -n "EvidencePacket|evidence packet|bounded|second pass|no_new_evidence|partial|limit|cost|ROI|human verification|not.*replacement|main.pdf|cost_benefit" demo/script.md demo/shot-list.md demo/recording-checklist.md
```

- [ ] Check demo package files exist:

```powershell
python -c "from pathlib import Path; paths=['demo/script.md','demo/shot-list.md','demo/recording-checklist.md','demo/final-video-notes.md']; [print(p, Path(p).exists(), Path(p).stat().st_size if Path(p).exists() else 0) for p in paths]"
```

- [ ] Run diff hygiene:

```powershell
git diff --check
```

## Subagent Plan

### Subagent A: Node 11 Demo Package Implementer

**Role:** worker.

**Write scope:** `demo/**`, `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`, `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`.

**Task:** Create the timed script, final shot map, recording checklist, optional static asset manifest, and final video notes. Do not modify app code, eval code, report contents, or claim values.

### Subagent B: Node 11 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Verify the package matches this stage plan:

- Script is 170-190 seconds by word count estimate.
- Shot list maps every spoken claim to a screen moment.
- Required screen moments are present.
- Recording checklist includes local server, seeded corpus, provider/model settings, browser zoom, fallback assets.
- Node 11 does not claim a final video exists if none was recorded.

### Subagent C: Node 11 Demo Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Review demo persuasiveness and claim boundaries:

- The 3-minute story is coherent and buyer-readable.
- The script is not too dense for a normal voiceover.
- Claims remain bounded to first-pass evidence gathering and human verification.
- Fallback plan is practical for recording.
- Residual risks are explicit.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 11:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 11 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 11 Gate

Node 11 is accepted only when:

- `demo/script.md`, `demo/shot-list.md`, `demo/recording-checklist.md`, and `demo/final-video-notes.md` exist.
- Script duration check passes.
- Required screen moments are covered.
- Spec review passes.
- Demo quality review passes.
- The package is explicitly marked recorder-ready unless an actual final video exists.
