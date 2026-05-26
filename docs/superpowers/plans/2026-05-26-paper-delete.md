# Paper Delete Implementation Plan

## Task 1: Backend Delete Endpoint

- Add failing tests in API paper route coverage for deleting a ready paper.
- Add `IngestionService.delete_paper(paper_id)`.
- Add `WorkspaceStore.remove_paper(paper_id)`.
- Add `DELETE /papers/{paper_id}` returning 204.
- Verify targeted backend tests pass.

## Task 2: Frontend Delete Control

- Add `paperMemoryApi.deletePaper`.
- Extend `PaperLibrary` with optional `onDeletePaper`.
- Show a delete button in Paper Manager cards.
- Wire `WorkspaceClient` to confirm, call API, and refresh local state.
- Verify frontend typecheck passes.

## Task 3: Final Verification

- Run full API tests.
- Run web typecheck.
- Run `git diff --check`.
- Use browser smoke test on `http://127.0.0.1:3000`.
