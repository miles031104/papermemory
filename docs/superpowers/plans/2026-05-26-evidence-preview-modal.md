# Evidence Preview Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the right-side retrieval evidence panel scrollable and let users open each page evidence result in a larger image/text preview.

**Architecture:** Keep the feature local to the existing web UI. `EvidencePanel` normalizes evidence, tracks the selected page result, and renders a modal dialog with the page image and caption text. CSS gives the chat aside a fixed-height scroll area and styles the preview modal without changing backend data contracts.

**Tech Stack:** Next.js React components, TypeScript, existing `ApiPageEvidence` image URLs and captions, CSS.

---

### Task 1: Evidence Panel Interaction

**Files:**
- Modify: `apps/web/components/evidence-panel.tsx`

- [ ] **Step 1: Record current missing behavior**

Use the browser DOM to confirm the evidence items are static cards without a dialog role or clickable detail trigger.

- [ ] **Step 2: Add selected evidence state**

Import `useEffect` and `useState`, normalize evidence as today, and keep `selectedEvidence` as the currently opened page result.

- [ ] **Step 3: Turn each evidence card into a button-like single-page row**

Make each list item contain a full-width button with page title, page number, confidence, optional thumbnail, and text preview. Keep existing ids such as `evidence-{paperId}-{page}` for citation anchors.

- [ ] **Step 4: Render detail modal**

When selected, render a dialog with the enlarged image, page metadata, and full text. Support close button, backdrop click, and Escape close.

### Task 2: Layout And Styling

**Files:**
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Make chat evidence panel scroll inside the right rail**

Add chat-specific panel height rules mirroring the Paper Manager right rail: `height: 100%`, `grid-template-rows: auto minmax(0, 1fr)`, and `overflow-y: auto` on `.panel__body`.

- [ ] **Step 2: Style evidence rows as compact page cards**

Keep thumbnails stable, text truncated in the row, and avoid horizontal overflow.

- [ ] **Step 3: Style modal preview**

Add fixed overlay, bounded preview image area, scrollable text area, and responsive single-column behavior on narrow screens.

### Task 3: Verification

**Files:**
- Verify: `apps/web/components/evidence-panel.tsx`
- Verify: `apps/web/app/globals.css`

- [ ] **Step 1: Run frontend typecheck**

Run: `npm --prefix apps/web run typecheck`

- [ ] **Step 2: Run whitespace diff check**

Run: `git -c safe.directory=D:/codex/papermemory -c core.whitespace=cr-at-eol diff --check`

- [ ] **Step 3: Browser smoke check**

Open Chat, verify the right evidence panel remains within the viewport, evidence rows are clickable, and opening one shows a dialog with image and text.
