# Paper Delete Design

## Goal

Add a local-first delete action for papers in Paper Manager so a user can remove an uploaded PDF and re-upload during testing without manually editing storage.

## Scope

- Add `DELETE /papers/{paper_id}` to the FastAPI API.
- Delete `storage/papers/{paper_id}` and `storage/rendered_pages/{paper_id}`.
- Remove the paper id from every workspace library and paper group.
- Return `204 No Content` on success.
- Return `404 Paper not found.` for unknown paper ids and `400 Invalid paper id.` for invalid ids.
- Add a Paper Manager delete button with browser confirmation before calling the API.
- After deletion, refresh paper, library, and group state so Chat and Paper Manager scopes stay consistent.

## Out Of Scope

- Recycle bin, undo, or restore.
- Conversation citation rewriting.
- Qdrant point deletion, because the current vector layer has no existing deletion method. File and workspace consistency is the required MVP behavior.

## Testing

- Backend API tests cover file deletion, rendered page deletion, workspace reference cleanup, 404 for missing papers, and invalid id rejection.
- Frontend typecheck covers API client and component wiring.
- Browser smoke test verifies the delete button appears in Paper Manager and the app has no console errors.
