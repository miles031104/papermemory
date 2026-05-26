# Library And Group Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe delete actions for PaperMemory libraries and paper groups without deleting local PDF/paper files.

**Architecture:** The FastAPI workspace store owns persisted deletion semantics and validation. The Next.js client exposes delete API helpers, keeps mock/offline behavior aligned, and renders compact icon actions in the research sidebar.

**Tech Stack:** FastAPI, Pydantic workspace schemas, pytest, Next.js React components, TypeScript, CSS.

---

### Task 1: Backend Workspace Deletion

**Files:**
- Modify: `apps/api/tests/test_workspace_store.py`
- Modify: `apps/api/app/services/workspace_store.py`
- Modify: `apps/api/app/routers/workspace.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert deleting a library removes only workspace references, deleting a custom group moves papers into the default group, and guarded deletes return `400`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest apps/api/tests/test_workspace_store.py -q`

Expected: failures for missing `DELETE /workspace/libraries/{id}` and `DELETE /workspace/paper-groups/{id}`.

- [ ] **Step 3: Implement minimal backend behavior**

Add `WorkspaceStore.delete_library()` and `WorkspaceStore.delete_paper_group()` plus router `DELETE` endpoints.

- [ ] **Step 4: Run backend tests**

Run: `python -m pytest apps/api/tests/test_workspace_store.py -q`

Expected: all workspace store tests pass.

### Task 2: Frontend API And State

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/components/workspace-client.tsx`
- Modify: `apps/web/components/research-sidebar.tsx`

- [ ] **Step 1: Add API helpers**

Add `deleteLibrary(libraryId, baseUrl?)` and `deletePaperGroup(groupId, baseUrl?)` using `requestVoid`.

- [ ] **Step 2: Add workspace client handlers**

Add persisted delete calls with workspace reload, and mock delete paths that preserve paper records while updating library/group/conversation state.

- [ ] **Step 3: Wire sidebar callbacks**

Pass `onDeleteLibrary` and `onDeleteGroup` into `ResearchSidebar`, confirm before deleting, and surface errors in the existing sidebar inline alert areas.

### Task 3: Sidebar UI Polish

**Files:**
- Modify: `apps/web/components/research-sidebar.tsx`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Avoid nested buttons**

Wrap each selectable row in a row container with one selection button and one compact delete icon button.

- [ ] **Step 2: Preserve compact sidebar layout**

Style delete buttons so library/group names keep ellipsis behavior and the sidebar does not gain horizontal scroll.

### Task 4: Verification

**Files:**
- Verify: `apps/api/tests/test_workspace_store.py`
- Verify: `apps/web`

- [ ] **Step 1: Run backend tests**

Run: `python -m pytest apps/api/tests/test_workspace_store.py -q`

- [ ] **Step 2: Run frontend typecheck**

Run: `npm --prefix apps/web run typecheck`

- [ ] **Step 3: Run whitespace diff check**

Run: `git -c safe.directory=D:/codex/papermemory -c core.whitespace=cr-at-eol diff --check`

- [ ] **Step 4: Browser smoke check**

Open the local PaperMemory UI and verify library/group delete buttons are visible, compact, and do not break the fixed-height Paper Manager layout.
