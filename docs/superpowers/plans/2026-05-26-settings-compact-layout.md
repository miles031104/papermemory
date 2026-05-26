# Settings Compact Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Settings view usable inside the fixed-height PaperMemory workspace by keeping daily settings visible and moving installation details into collapsible sections.

**Architecture:** Keep existing React state and localStorage persistence unchanged. Reorganize only the Settings components and CSS: high-frequency chat/API fields remain visible, while install/runtime diagnostics use native `<details>/<summary>` disclosure sections.

**Tech Stack:** Next.js, React, TypeScript, CSS, Browser layout measurement.

---

### Task 1: Compact Chat Model Settings

**Files:**
- Modify: `apps/web/components/model-settings-panel.tsx`
- Modify: `apps/web/app/globals.css`

- [x] Move provider company, base URL, model, API key, image context, and max evidence images into the always-visible part of the model panel.
- [x] Move the fixed provider selector, temperature, retrieval top-k, and require-evidence toggle into a collapsed `<details>`.
- [x] Preserve all existing `ModelSettings` fields and `onChange` behavior.

### Task 2: Collapse Install Setup Details

**Files:**
- Modify: `apps/web/components/setup-wizard.tsx`
- Modify: `apps/web/app/globals.css`

- [x] Keep only the FastAPI URL field always visible in SetupWizard.
- [x] Move install mode/local services, VisRAG/Hugging Face, and generated env/commands into disclosure sections.
- [x] Sync BYOK env values from `Model settings` instead of maintaining a second provider form.
- [x] Remove `Apply to chat`; `Model settings` is now the single source for generation provider and multimodal values.

### Task 3: Verify Fixed-Height Settings

**Files:**
- Modify: `apps/web/app/globals.css`

- [x] Ensure `.settings-view` and `.settings-view__content` fit the fixed workspace height.
- [x] Run `npm --prefix apps/web run typecheck`.
- [x] Run `git -c safe.directory=D:/codex/papermemory -c core.whitespace=cr-at-eol diff --check`.
- [x] Browser-check Settings at 1280x720: no page-level scroll, visible model/runtime panels, disclosure controls present, no console errors.
