# PaperMemory Paper Library Groups Design

Version: v1.0
Status: Approved for implementation planning
Date: 2026-05-26

## Context

PaperMemory is a local-first PDF research workspace. Its stable pipeline is PDF upload, page rendering, VisRAG-style retrieval, Qdrant page evidence, and BYOK multimodal chat. The current app already has local workspace persistence for libraries, conversations, and paper groups, but the UI still treats paper management and chat as one crowded workspace surface.

The reference project `miles031104/paperlibrary` shows a useful direction: a paper library should be a searchable, filterable, structured management interface, not only a PDF upload list. PaperMemory should absorb that product idea while keeping its own core value: group-scoped RAG chat over local page evidence.

## Goals

- Provide a clear interface for managing local paper libraries.
- Add a first-class group workflow where each group is its own RAG scope.
- Keep one paper in exactly one group within a library.
- Let users upload directly into the currently selected group.
- Let users switch between Home, Chat, Paper Manager, and Settings from the left side.
- Keep Chat and Paper Manager as separate work surfaces that share the active group.
- Preserve local-first storage, API-side secret handling, existing VisRAG/Qdrant retrieval, and streaming chat.

## Non-Goals

- Do not introduce cloud sync, accounts, collaboration, or SaaS concepts.
- Do not create one Qdrant collection per group in the MVP.
- Do not support multi-group chat scopes in the MVP.
- Do not build full LLM metadata extraction in this slice. The UI may leave room for title, topics, year, venue, summaries, and details, but this implementation focuses on group-scoped management and chat.

## Information Architecture

The primary hierarchy is:

```text
Library -> Group -> Paper
```

`Library` is the broad research project container, such as "AI Agents Reading List".

`Group` is the active RAG unit, such as "VisRAG Core" or "Agent Safety". Each group owns a list of paper IDs and is the only scope used by Chat and retrieval.

`Paper` belongs to exactly one group within a library. Moving a paper to a new group removes it from its previous group in the same library.

Every library has a default `Ungrouped uploads` group. Uploads with no explicit group go there. This default group is also a valid RAG scope.

## Navigation Model

The app becomes a layered workspace instead of showing every workflow at once.

The left sidebar has two jobs:

- App view navigation: `Home`, `Chat`, `Paper Manager`, `Settings`.
- Scope navigation: a `Library -> Group` tree.

The selected group is global workspace state. Chat and Paper Manager both use the same active group, but they are displayed on separate views.

### Home

Home uses the current hero/summary area as an entry screen. It should show:

- Current active library and group.
- Counts for papers, ready papers, indexed pages, and groups.
- Recent conversation or indexing status when available.
- Entry buttons for `Enter Chat`, `Manage Paper Library`, and `Settings`.

Home is an opening guide, not a permanent top section above every workflow.

### Chat

Chat is dedicated to conversation and evidence.

- Header displays `Chat with: {group.name}`.
- Scope summary displays the active group paper count and page count.
- If the group has no ready papers, the UI says this group has no searchable papers yet.
- Asking a question sends only the active group `paperIds` to `/chat`.
- Evidence panel shows only results retrieved from the active group scope.

### Paper Manager

Paper Manager is dedicated to library organization.

- Header displays the active group name.
- Upload button uploads into the active group.
- Paper cards list only papers in the active group.
- Search filters papers by title, filename, and later metadata fields.
- Status filters support ready, indexing, queued, and error.
- Each paper card has a move action for changing groups.
- Moving a paper to another group automatically removes it from its old group.

### Settings

Settings remains dedicated to local API, BYOK model, VisRAG, multimodal, and storage configuration.

## Backend Design

The backend should extend the existing `WorkspaceStore`; it should not introduce a new database system for this feature.

Existing models remain:

- `ResearchLibrary`
- `PaperGroup`
- `ResearchConversation`

`PaperGroup` becomes the authoritative RAG scope. The backend must enforce unique paper membership across groups within the same library.

### API Surface

Keep existing endpoints:

- `GET /workspace`
- `POST /workspace/libraries`
- `PATCH /workspace/libraries/{library_id}`
- `POST /workspace/libraries/{library_id}/paper-groups`
- `PATCH /workspace/paper-groups/{group_id}`
- `POST /workspace/libraries/{library_id}/conversations`
- `PATCH /workspace/conversations/{conversation_id}`

Add a focused move endpoint:

```http
POST /workspace/paper-groups/{group_id}/papers/{paper_id}
```

Behavior:

- Validate that the target group exists.
- Validate that the paper exists.
- Validate that the paper belongs to the same library.
- Add the paper to the target group.
- Remove the paper from all other groups in that library.
- Ensure the paper is present in the library `paper_ids`.
- Return the updated `PaperGroup`.

For upload, the frontend can continue to call `/papers/upload`, then call the move endpoint with the active group. This keeps ingestion and workspace assignment separate.

### Retrieval and Chat Scope

No new retrieval endpoint is required for MVP. Frontend resolves the active group to `paperIds` and passes them to:

- `/retrieval/search`
- `/chat`

The backend already supports scoped retrieval through `paper_ids`. The implementation should preserve the current behavior where an empty scope returns no evidence or conversation mode rather than accidentally searching all papers.

## Frontend Design

The current `WorkspaceClient` should be decomposed enough to keep views understandable:

- `HomeView`
- `ChatView`
- `PaperManagerView`
- `SettingsView`
- shared `ResearchSidebar`
- shared mapping helpers for API models

This can be done incrementally without a large rewrite. The first implementation may keep state in `WorkspaceClient` while extracting visual sections into components.

### State

Frontend state should track:

- `activeView`: `home | chat | papers | settings`
- `activeLibraryId`
- `activeGroupId`
- libraries, groups, conversations, papers
- selected conversation for the active library or group

When the active library changes:

- If it has groups, select the first group or its default ungrouped group.
- If it has no groups, create or repair the default group through backend loading behavior.

When the active group changes:

- Chat scope changes to that group.
- Paper Manager list changes to that group.
- Evidence from the previous group is cleared.

### Upload Flow

1. User opens Paper Manager with an active group.
2. User uploads a PDF.
3. Frontend calls `/papers/upload`.
4. Frontend calls `POST /workspace/paper-groups/{activeGroupId}/papers/{paperId}`.
5. Frontend refreshes workspace and paper list.
6. The paper appears in the active group immediately.

### Move Flow

1. User clicks `Move group` on a paper card.
2. User chooses another group in the same library.
3. Frontend calls the move endpoint.
4. Frontend refreshes workspace.
5. The paper disappears from the old group and appears in the new group.

### Chat Flow

1. User opens Chat with an active group.
2. Frontend computes `activeGroupPaperIds`.
3. Only ready papers from that group are sent to chat and retrieval.
4. The chat header and evidence note name the active group.

## Migration and Repair

Existing workspaces may have:

- libraries with `paper_ids` but no groups,
- groups with overlapping paper IDs,
- missing `Ungrouped uploads` groups,
- old conversations scoped only to a library.

Repair behavior on workspace load:

- Ensure every library has at least one default group.
- Assign any library paper not present in a group to `Ungrouped uploads`.
- If a paper appears in multiple groups in the same library, keep the first occurrence and remove later duplicates.
- Preserve existing conversations as library-level conversations for now. Chat scope comes from the currently selected group, not from old conversation metadata.

## Error Handling

- If the user tries to chat with an empty group, show a friendly empty-scope message.
- If a paper move fails, keep the UI state unchanged and show the API error.
- If upload succeeds but group assignment fails, show the paper in library-level data and offer retry assignment to the active group.
- If a group is deleted in a future feature, papers should move to `Ungrouped uploads`; group deletion is not part of this MVP.

## Testing Strategy

Backend tests:

- Default workspace creates `Ungrouped uploads`.
- Existing library papers are assigned to the default group during repair.
- Creating a group works.
- Moving a paper into a group removes it from other groups in the same library.
- Moving a paper into a group ensures the library includes that paper.
- Moving an unknown paper returns 400.
- Moving a paper to a group from another library is rejected.
- Scoped retrieval still returns only active group papers.
- Empty group chat does not call vector retrieval.

Frontend tests or type checks:

- TypeScript typecheck passes.
- Active group paper IDs drive chat request `paper_ids`.
- Upload flow calls group assignment after upload.
- Moving paper updates workspace state and clears stale evidence.
- Home, Chat, Paper Manager, and Settings views render from the same active group state.

Manual verification:

- Open the app at localhost.
- Create a library and groups.
- Upload into a selected group.
- Move a paper to another group.
- Ask a question in Chat and confirm evidence comes only from the active group.

## Acceptance Criteria

- User can switch among Home, Chat, Paper Manager, and Settings.
- User can select a group from the sidebar.
- User can upload a PDF into the selected group.
- User can move a paper between groups.
- A paper belongs to only one group within a library.
- Chat uses only the selected group as its RAG scope.
- Empty groups do not accidentally search all papers.
- Existing workspace data is repaired into a safe default group structure.
- Existing streaming chat, multimodal image evidence, Markdown rendering, citation navigation, and local settings persistence continue to work.
