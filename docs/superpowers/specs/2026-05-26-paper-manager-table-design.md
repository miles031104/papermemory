# Paper Manager Table View Design

Version: v1.0
Status: Draft for review
Date: 2026-05-26

## Context

PaperMemory now has a separate Paper Manager view, group-scoped paper management, upload, move, and delete actions. The current Paper Manager layout still behaves like an upload page with a paper card list on the side. For a growing local paper library, the main surface should become a scan-friendly management interface.

The chosen direction is the professional library manager layout: Paper Manager defaults to a table view, keeps cards as an alternate view, and moves upload into a top-level action button.

## Goals

- Make Paper Manager useful as the primary paper library management screen.
- Show existing papers in a table by default.
- Let users switch between table and card presentation.
- Keep upload available as a top button instead of a permanently expanded central panel.
- Preserve existing move group and delete paper behavior.
- Keep the fixed one-screen workspace without page-level vertical scrolling on desktop.
- Keep the backend unchanged for this slice.

## Non-Goals

- Do not add server-side search, sorting, pagination, or metadata extraction in this slice.
- Do not add batch selection or bulk actions yet.
- Do not change group membership semantics.
- Do not alter upload, move, delete, or chat API contracts.

## Layout

Paper Manager becomes a three-part management workspace:

- Header/tool row: active group name, paper counts, table/card switch, and an `Upload paper` button.
- Main table surface: existing papers in the active group, optimized for scanning.
- Inspector/action area: selected paper details and management actions.

The upload form opens from the top button as an inline drawer or compact panel within Paper Manager. It should not occupy the default view when the user is managing existing papers. If upload succeeds, the drawer can stay open with status feedback or collapse after the existing upload state clears, whichever best matches the current component flow.

## Table View

The table should show the fields available in `PaperSummary`:

- Title
- Authors
- Year
- Pages
- Status
- Index progress
- Group action
- Delete action

The table is the default view. Rows should be compact, readable, and stable in height. Long titles and author lists truncate cleanly instead of resizing the layout. Status should reuse `StatusBadge`. Index progress can be a slim progress bar or percentage text, whichever fits the fixed-height page better.

Selecting a row marks it visually and feeds the inspector. Row selection is local UI state only.

## Card View

Card view remains available for users who prefer the existing paper list presentation. It should reuse the current `PaperLibraryBody` card content where practical, so move/delete behavior stays consistent.

The view switch should not reset the active group or lose upload state.

## Upload Flow

The `Upload paper` button lives in the Paper Manager header/tool row. Clicking it toggles the existing `PaperUploadPanel` in a compact drawer or panel below the tool row.

The upload form keeps the existing props and behavior:

- `uploadTitle`
- `selectedFile`
- `fileInputKey`
- `isUploading`
- `uploadMessage`
- `uploadError`
- `onTitleChange`
- `onFileChange`
- `onUpload`

This feature only changes where the panel appears.

## Component Boundaries

`PaperManagerView` owns the layout, upload drawer state, and active selected paper ID.

`PaperLibrary` should become a reusable display component that can render either:

- table mode for management
- card mode for the existing card presentation

Move/delete callbacks stay as props. No API calls should move into presentation components.

## Empty And Error States

If the active group has no papers, the table area should show a quiet empty state with an upload action.

If a paper has `error` status, the row should make that state visible through `StatusBadge` and still allow delete/move. Reindex is not required in this slice because no existing frontend API is available for it.

## Accessibility

- The table uses semantic table markup.
- The view switch is a segmented control or tab-like button group with clear active state.
- Delete remains a real button.
- Move group remains a select control with visible label text.
- Upload drawer toggle has an accessible expanded/collapsed state.

## Verification

- TypeScript typecheck passes.
- `git diff --check` passes.
- Browser check at 1280x720 confirms no page-level scroll in Paper Manager.
- Browser check confirms table view is default, card view can be selected, upload opens from the top button, and move/delete controls are present.
