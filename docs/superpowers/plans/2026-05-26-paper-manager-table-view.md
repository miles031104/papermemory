# Paper Manager Table View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Paper Manager into a table-first paper library management screen with a top upload button and card/table view switching.

**Architecture:** Keep backend contracts unchanged. `PaperManagerView` owns UI state for table/card mode, upload drawer visibility, and selected paper; `PaperLibrary` becomes a reusable display component that renders table or card mode while keeping move/delete callbacks as props.

**Tech Stack:** Next.js, React state, TypeScript, existing CSS, existing Browser verification.

---

### Task 1: Add Table/Card Rendering To PaperLibrary

**Files:**
- Modify: `apps/web/components/paper-library.tsx`
- Modify: `apps/web/app/globals.css`

- [x] Add `viewMode?: "table" | "cards"`, `selectedPaperId?: string`, and `onSelectPaper?: (paperId: string) => void` props to `PaperLibrary`.
- [x] Keep the existing card list path available when `viewMode` is `"cards"` or omitted.
- [x] Add a semantic table path for `viewMode="table"` with columns: title, authors, year, pages, status, progress, group, actions.
- [x] Reuse `StatusBadge`, `onMovePaper`, and `onDeletePaper`; do not add API calls inside `PaperLibrary`.
- [x] Style table rows so long titles/authors truncate and row heights remain stable.

### Task 2: Rework PaperManagerView Into A Table-First Workspace

**Files:**
- Modify: `apps/web/components/paper-manager-view.tsx`
- Modify: `apps/web/app/globals.css`

- [x] Add local state for `viewMode`, `isUploadOpen`, and `selectedPaperId`.
- [x] Replace the old upload-first main layout with a manager panel that contains active group summary, view switch, and `Upload paper` button.
- [x] Render `PaperUploadPanel` only when the upload drawer is open.
- [x] Render `PaperLibrary` in table mode by default and card mode when selected.
- [x] Add an inspector panel that shows selected paper title, authors, year, page count, status, progress, and management hint text.
- [x] Preserve fixed-height desktop behavior and avoid page-level scroll.

### Task 3: Verify Behavior And Layout

**Files:**
- Verify: `apps/web/components/paper-library.tsx`
- Verify: `apps/web/components/paper-manager-view.tsx`
- Verify: `apps/web/app/globals.css`

- [x] Run `npm --prefix apps/web run typecheck`; expected exit code 0.
- [x] Run `git -c safe.directory=D:/codex/papermemory -c core.whitespace=cr-at-eol diff --check`; expected exit code 0.
- [x] Browser-check Paper Manager at 1280x720: table view is default, upload is hidden until the top button opens it, card view can be selected, move/delete controls are present, and there is no page-level scroll.
