# Paper Library Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a layered PaperMemory workspace where each `Library -> Group` owns a unique paper set and Chat/Paper Manager use the selected group as the RAG scope.

**Architecture:** Extend the existing JSON-backed `WorkspaceStore` and FastAPI workspace router instead of adding a new database. Keep retrieval/chat scoped by passing the selected group's `paper_ids` to existing `/retrieval/search` and `/chat`. Split the frontend into Home, Chat, Paper Manager, and Settings views sharing one active group state.

**Tech Stack:** FastAPI, Pydantic, local JSON workspace files, Next.js/React/TypeScript, existing VisRAG/Qdrant services, pytest, `npm --prefix apps/web run typecheck`.

---

## File Structure

- Modify `apps/api/app/services/workspace_store.py`
  - Enforce one group membership per paper inside a library.
  - Repair missing default groups and duplicate group membership on workspace load.
  - Add `move_paper_to_group(group_id, paper_id)`.
- Modify `apps/api/app/routers/workspace.py`
  - Add `POST /workspace/paper-groups/{group_id}/papers/{paper_id}`.
- Modify `apps/api/tests/test_workspace_store.py`
  - Add backend contract tests for default group repair, unique group membership, and the move endpoint.
- Modify `apps/web/lib/types.ts`
  - Extend `WorkspaceView`-adjacent typing if needed by components.
  - Reuse existing `PaperGroup`, `ResearchLibrary`, and `PaperSummary`.
- Modify `apps/web/lib/api.ts`
  - Add `movePaperToGroup(groupId, paperId, baseUrl?)`.
- Modify `apps/web/components/research-sidebar.tsx`
  - Change view navigation to `Home`, `Chat`, `Paper Manager`, `Settings`.
  - Render `Library -> Group` tree.
  - Add group creation form scoped to active library.
- Create `apps/web/components/home-view.tsx`
  - Entry dashboard using the existing hero concept.
- Create `apps/web/components/paper-manager-view.tsx`
  - Group-scoped paper management, upload, search/filter, and move controls.
- Create `apps/web/components/chat-view.tsx`
  - Group-scoped chat layout using existing `ChatPanel` and `EvidencePanel`.
- Modify `apps/web/components/paper-library.tsx`
  - Add optional move controls and searchable group-scoped card behavior.
- Modify `apps/web/components/workspace-client.tsx`
  - Track `activeView` and `activeGroupId`.
  - Compute active group papers and ready group paper IDs.
  - Route uploads and chat through the active group.
- Modify `apps/web/app/globals.css`
  - Add styles for the layered workspace, group tree, home dashboard, paper manager controls, and move controls.

---

### Task 1: Backend Group Repair and Unique Membership

**Files:**
- Modify: `apps/api/app/services/workspace_store.py`
- Test: `apps/api/tests/test_workspace_store.py`

- [ ] **Step 1: Add failing workspace repair tests**

Append these tests to `apps/api/tests/test_workspace_store.py`:

```python
def test_workspace_repair_assigns_library_papers_to_default_group(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-orphan")
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True)
    now = datetime.now(UTC).isoformat()
    (workspace_dir / "libraries.json").write_text(
        json.dumps(
            [
                {
                    "id": "library-custom",
                    "name": "Custom",
                    "description": "",
                    "paper_ids": ["paper-orphan"],
                    "group_ids": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        ),
        encoding="utf-8",
    )
    (workspace_dir / "conversations.json").write_text("[]", encoding="utf-8")
    (workspace_dir / "paper_groups.json").write_text("[]", encoding="utf-8")

    client = _client(tmp_path)
    body = client.get("/workspace").json()

    library = body["libraries"][0]
    assert library["id"] == "library-custom"
    assert len(body["paper_groups"]) == 1
    group = body["paper_groups"][0]
    assert group["library_id"] == "library-custom"
    assert group["name"] == "Ungrouped uploads"
    assert group["paper_ids"] == ["paper-orphan"]
    assert library["group_ids"] == [group["id"]]


def test_workspace_repair_removes_duplicate_group_membership_within_library(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-shared")
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True)
    now = datetime.now(UTC).isoformat()
    (workspace_dir / "libraries.json").write_text(
        json.dumps(
            [
                {
                    "id": "library-custom",
                    "name": "Custom",
                    "description": "",
                    "paper_ids": ["paper-shared"],
                    "group_ids": ["group-a", "group-b"],
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        ),
        encoding="utf-8",
    )
    (workspace_dir / "conversations.json").write_text("[]", encoding="utf-8")
    (workspace_dir / "paper_groups.json").write_text(
        json.dumps(
            [
                {
                    "id": "group-a",
                    "library_id": "library-custom",
                    "name": "A",
                    "description": "",
                    "paper_ids": ["paper-shared"],
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "group-b",
                    "library_id": "library-custom",
                    "name": "B",
                    "description": "",
                    "paper_ids": ["paper-shared"],
                    "created_at": now,
                    "updated_at": now,
                },
            ]
        ),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    groups = client.get("/workspace").json()["paper_groups"]

    assert next(group for group in groups if group["id"] == "group-a")["paper_ids"] == ["paper-shared"]
    assert next(group for group in groups if group["id"] == "group-b")["paper_ids"] == []
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\codex\papermemory\apps\api;D:\codex\papermemory\apps\api\.venv\Lib\site-packages;D:\codex\papermemory\apps\api\.venv\Lib\site-packages\win32;D:\codex\papermemory\apps\api\.venv\Lib\site-packages\win32\lib'; $env:PATH='D:\codex\papermemory\apps\api\.venv\Lib\site-packages\pywin32_system32;' + $env:PATH; & 'C:\Users\Miles CUI\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest apps/api/tests/test_workspace_store.py -q
```

Expected: at least the two new tests fail because the store preserves an empty group list and does not dedupe group membership.

- [ ] **Step 3: Implement workspace repair helpers**

In `apps/api/app/services/workspace_store.py`, add this constant near the existing default IDs:

```python
DEFAULT_GROUP_NAME = "Ungrouped uploads"
DEFAULT_GROUP_DESCRIPTION = "Default local-first group for papers that have not been organized yet."
```

Then replace hardcoded `"Ungrouped uploads"` and its default description in `_ensure_defaults()` and `_repair_empty_workspace()` with those constants.

Add these helper methods inside `WorkspaceStore`:

```python
    def _repair_workspace_integrity(self, workspace: WorkspaceResponse) -> WorkspaceResponse:
        changed = False
        now = self._now()
        groups_by_library: dict[str, list[PaperGroup]] = {
            library.id: [group for group in workspace.paper_groups if group.library_id == library.id]
            for library in workspace.libraries
        }

        next_groups: list[PaperGroup] = list(workspace.paper_groups)
        next_libraries: list[ResearchLibrary] = []

        for library in workspace.libraries:
            library_groups = groups_by_library.get(library.id, [])
            if not library_groups:
                default_group = PaperGroup(
                    id=self._new_id("group"),
                    library_id=library.id,
                    name=DEFAULT_GROUP_NAME,
                    description=DEFAULT_GROUP_DESCRIPTION,
                    paper_ids=[],
                    created_at=now,
                    updated_at=now,
                )
                next_groups.append(default_group)
                library_groups = [default_group]
                changed = True

            seen_paper_ids: set[str] = set()
            repaired_groups: list[PaperGroup] = []
            for group in library_groups:
                unique_group_papers: list[str] = []
                for paper_id in group.paper_ids:
                    if paper_id in seen_paper_ids:
                        changed = True
                        continue
                    if paper_id not in library.paper_ids:
                        changed = True
                        continue
                    seen_paper_ids.add(paper_id)
                    unique_group_papers.append(paper_id)
                if unique_group_papers != group.paper_ids:
                    group = group.model_copy(update={"paper_ids": unique_group_papers, "updated_at": now})
                repaired_groups.append(group)

            missing_paper_ids = [paper_id for paper_id in library.paper_ids if paper_id not in seen_paper_ids]
            if missing_paper_ids:
                default_group = self._default_group_for_library(repaired_groups)
                repaired_groups = [
                    group.model_copy(
                        update={
                            "paper_ids": self._dedupe([*group.paper_ids, *missing_paper_ids]),
                            "updated_at": now,
                        }
                    )
                    if group.id == default_group.id
                    else group
                    for group in repaired_groups
                ]
                changed = True

            repaired_group_ids = [group.id for group in repaired_groups]
            if library.group_ids != repaired_group_ids:
                library = library.model_copy(update={"group_ids": repaired_group_ids, "updated_at": now})
                changed = True
            next_libraries.append(library)

            repaired_by_id = {group.id: group for group in repaired_groups}
            next_groups = [repaired_by_id.get(group.id, group) for group in next_groups]

        repaired = WorkspaceResponse(
            libraries=next_libraries,
            conversations=workspace.conversations,
            paper_groups=[group for group in next_groups if any(group.library_id == library.id for library in next_libraries)],
        )
        if changed:
            self._write_workspace(repaired)
        return repaired

    def _default_group_for_library(self, groups: list[PaperGroup]) -> PaperGroup:
        for group in groups:
            if group.name == DEFAULT_GROUP_NAME:
                return group
        return groups[0]
```

Then update `_load_workspace()` so it repairs before returning:

```python
    def _load_workspace(self) -> WorkspaceResponse:
        if not self._defaults_initialized:
            self._ensure_defaults()
            self._defaults_initialized = True
        workspace = WorkspaceResponse(
            libraries=self._read_list(self.libraries_path, ResearchLibrary),
            conversations=self._read_list(self.conversations_path, ResearchConversation),
            paper_groups=self._read_list(self.paper_groups_path, PaperGroup),
        )
        if not workspace.libraries:
            return self._repair_empty_workspace()
        return self._repair_workspace_integrity(workspace)
```

- [ ] **Step 4: Run workspace store tests**

Run the same command from Step 2.

Expected: all `test_workspace_store.py` tests pass.

- [ ] **Step 5: Commit backend repair**

Run:

```powershell
git -c safe.directory=D:/codex/papermemory add apps/api/app/services/workspace_store.py apps/api/tests/test_workspace_store.py
git -c safe.directory=D:/codex/papermemory commit -m "feat: repair paper group scopes"
```

---

### Task 2: Backend Move Paper Endpoint

**Files:**
- Modify: `apps/api/app/services/workspace_store.py`
- Modify: `apps/api/app/routers/workspace.py`
- Test: `apps/api/tests/test_workspace_store.py`

- [ ] **Step 1: Add failing move endpoint tests**

Append these tests to `apps/api/tests/test_workspace_store.py`:

```python
def test_move_paper_to_group_removes_it_from_previous_group(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-move")
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]
    group_a = client.post(
        f"/workspace/libraries/{library_id}/paper-groups",
        json={"name": "Group A", "paper_ids": ["paper-move"]},
    ).json()
    group_b = client.post(
        f"/workspace/libraries/{library_id}/paper-groups",
        json={"name": "Group B"},
    ).json()

    response = client.post(f"/workspace/paper-groups/{group_b['id']}/papers/paper-move")

    assert response.status_code == 200
    assert response.json()["paper_ids"] == ["paper-move"]
    groups = client.get("/workspace").json()["paper_groups"]
    assert next(group for group in groups if group["id"] == group_a["id"])["paper_ids"] == []
    assert next(group for group in groups if group["id"] == group_b["id"])["paper_ids"] == ["paper-move"]


def test_move_paper_to_group_adds_paper_to_library_scope(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-new-upload")
    client = _client(tmp_path)
    custom = client.post("/workspace/libraries", json={"name": "Custom database"}).json()
    group = client.post(
        f"/workspace/libraries/{custom['id']}/paper-groups",
        json={"name": "Target group"},
    ).json()

    response = client.post(f"/workspace/paper-groups/{group['id']}/papers/paper-new-upload")

    assert response.status_code == 200
    assert response.json()["paper_ids"] == ["paper-new-upload"]
    library = next(
        library
        for library in client.get("/workspace").json()["libraries"]
        if library["id"] == custom["id"]
    )
    assert library["paper_ids"] == ["paper-new-upload"]


def test_move_unknown_paper_to_group_returns_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]
    group = client.post(
        f"/workspace/libraries/{library_id}/paper-groups",
        json={"name": "Target group"},
    ).json()

    response = client.post(f"/workspace/paper-groups/{group['id']}/papers/missing-paper")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown paper id: missing-paper"
```

- [ ] **Step 2: Run move tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\codex\papermemory\apps\api;D:\codex\papermemory\apps\api\.venv\Lib\site-packages;D:\codex\papermemory\apps\api\.venv\Lib\site-packages\win32;D:\codex\papermemory\apps\api\.venv\Lib\site-packages\win32\lib'; $env:PATH='D:\codex\papermemory\apps\api\.venv\Lib\site-packages\pywin32_system32;' + $env:PATH; & 'C:\Users\Miles CUI\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest apps/api/tests/test_workspace_store.py -q
```

Expected: tests fail with 404 for the missing route.

- [ ] **Step 3: Implement `move_paper_to_group`**

Add this method to `WorkspaceStore`:

```python
    def move_paper_to_group(self, group_id: str, paper_id: str) -> PaperGroup:
        self._validate_id(group_id, "Invalid paper group id.")
        workspace = self._load_workspace()
        target_index, target_group = self._find_paper_group(workspace, group_id)
        validated_paper_id = self._validate_existing_paper_ids([paper_id])[0]
        library_index, library = self._find_library(workspace, target_group.library_id)
        now = self._now()

        next_library_paper_ids = self._dedupe([*library.paper_ids, validated_paper_id])
        workspace.libraries[library_index] = library.model_copy(
            update={"paper_ids": next_library_paper_ids, "updated_at": now}
        )

        updated_target = target_group.model_copy(
            update={
                "paper_ids": self._dedupe([*target_group.paper_ids, validated_paper_id]),
                "updated_at": now,
            }
        )
        workspace.paper_groups[target_index] = updated_target

        for index, group in enumerate(workspace.paper_groups):
            if group.library_id != target_group.library_id or group.id == target_group.id:
                continue
            if validated_paper_id not in group.paper_ids:
                continue
            workspace.paper_groups[index] = group.model_copy(
                update={
                    "paper_ids": [item for item in group.paper_ids if item != validated_paper_id],
                    "updated_at": now,
                }
            )

        self._write_workspace(workspace)
        return updated_target
```

- [ ] **Step 4: Add the router endpoint**

In `apps/api/app/routers/workspace.py`, add this route after `update_paper_group`:

```python
@router.post("/paper-groups/{group_id}/papers/{paper_id}", response_model=PaperGroup)
def move_paper_to_group(
    group_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    paper_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> PaperGroup:
    return store.move_paper_to_group(group_id=group_id, paper_id=paper_id)
```

- [ ] **Step 5: Run move tests**

Run the command from Step 2.

Expected: all `test_workspace_store.py` tests pass.

- [ ] **Step 6: Commit move endpoint**

Run:

```powershell
git -c safe.directory=D:/codex/papermemory add apps/api/app/services/workspace_store.py apps/api/app/routers/workspace.py apps/api/tests/test_workspace_store.py
git -c safe.directory=D:/codex/papermemory commit -m "feat: move papers between groups"
```

---

### Task 3: Frontend API Types and Group Move Client

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/types.ts`

- [ ] **Step 1: Add API client method**

In `apps/web/lib/api.ts`, add this method inside `paperMemoryApi` after `updatePaperGroup`:

```ts
  movePaperToGroup(groupId: string, paperId: string, baseUrl?: string) {
    return requestJson<ApiPaperGroup>(`/workspace/paper-groups/${groupId}/papers/${paperId}`, {
      method: "POST",
      baseUrl
    });
  },
```

- [ ] **Step 2: Add view type**

In `apps/web/lib/types.ts`, add this exported type near the workspace interfaces:

```ts
export type WorkspaceView = "home" | "chat" | "papers" | "settings";
```

- [ ] **Step 3: Update `ResearchSidebar` import during sidebar work**

When Task 4 modifies `research-sidebar.tsx`, import `WorkspaceView` from `@/lib/types` instead of declaring the old local type.

- [ ] **Step 4: Run frontend typecheck**

Run:

```powershell
npm --prefix apps/web run typecheck
```

Expected: typecheck passes.

- [ ] **Step 5: Commit frontend API support**

Run:

```powershell
git -c safe.directory=D:/codex/papermemory add apps/web/lib/api.ts apps/web/lib/types.ts
git -c safe.directory=D:/codex/papermemory commit -m "feat(web): add group move API client"
```

---

### Task 4: Sidebar View Navigation and Group Tree

**Files:**
- Modify: `apps/web/components/research-sidebar.tsx`
- Modify: `apps/web/components/workspace-client.tsx`

- [ ] **Step 1: Update sidebar props**

In `apps/web/components/research-sidebar.tsx`, replace the local `WorkspaceView` declaration with:

```ts
import type { PaperGroup, PaperSummary, ResearchConversation, ResearchLibrary, WorkspaceView } from "@/lib/types";
```

Update `ResearchSidebarProps` to include groups and group handlers:

```ts
interface ResearchSidebarProps {
  libraries: ResearchLibrary[];
  groups: PaperGroup[];
  conversations: ResearchConversation[];
  papers: PaperSummary[];
  activeLibraryId: string;
  activeGroupId: string;
  activeConversationId: string;
  activeView: WorkspaceView;
  apiLabel: string;
  apiConnection: "checking" | "online" | "offline";
  isPersisted: boolean;
  onViewChange: (view: WorkspaceView) => void;
  onSelectLibrary: (libraryId: string) => void;
  onSelectGroup: (groupId: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onCreateConversation: () => void;
  onCreateLibrary: (name: string, description: string) => Promise<void>;
  onCreateGroup: (name: string, description: string) => Promise<void>;
}
```

- [ ] **Step 2: Add group creation state**

Inside `ResearchSidebar`, add:

```ts
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [isSubmittingGroup, setIsSubmittingGroup] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);
```

Add `activeLibraryGroups`:

```ts
  const activeLibraryGroups = groups.filter((group) => group.libraryId === activeLibraryId);
```

- [ ] **Step 3: Add group submit handler**

Add this handler after `handleSubmitDatabase`:

```ts
  const handleSubmitGroup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = groupName.trim();
    if (!trimmedName) {
      setGroupError("Name is required.");
      return;
    }

    setIsSubmittingGroup(true);
    setGroupError(null);
    try {
      await onCreateGroup(trimmedName, groupDescription.trim());
      setGroupName("");
      setGroupDescription("");
      setIsCreatingGroup(false);
    } catch (error) {
      setGroupError(error instanceof Error ? error.message : "Could not create group.");
    } finally {
      setIsSubmittingGroup(false);
    }
  };
```

- [ ] **Step 4: Replace view nav buttons**

Replace the two old view buttons with four buttons:

```tsx
      <div className="sidebar-view-nav" role="tablist" aria-label="Workspace views">
        {[
          ["home", "Home"],
          ["chat", "Chat"],
          ["papers", "Paper Manager"],
          ["settings", "Settings"],
        ].map(([view, label]) => (
          <button
            className={`sidebar-view-nav__item${activeView === view ? " sidebar-view-nav__item--active" : ""}`}
            type="button"
            role="tab"
            aria-selected={activeView === view}
            onClick={() => onViewChange(view as WorkspaceView)}
            key={view}
          >
            {label}
          </button>
        ))}
      </div>
```

- [ ] **Step 5: Render group tree under databases**

Inside the library list render, after each library button, render its groups:

```tsx
                {groups
                  .filter((group) => group.libraryId === library.id)
                  .map((group) => {
                    const isActiveGroup = group.id === activeGroupId;
                    return (
                      <button
                        className={`sidebar-item sidebar-item--group${isActiveGroup ? " sidebar-item--active" : ""}`}
                        key={group.id}
                        type="button"
                        onClick={() => {
                          if (library.id !== activeLibraryId) {
                            onSelectLibrary(library.id);
                          }
                          onSelectGroup(group.id);
                        }}
                      >
                        <span className="sidebar-item__title">{group.name}</span>
                        <span className="sidebar-item__meta">{group.paperIds.length} papers</span>
                      </button>
                    );
                  })}
```

If the current JSX structure only allows one button per map item, wrap each library and its groups in a `<div className="sidebar-tree-node" key={library.id}>`.

- [ ] **Step 6: Add create group form**

After the database list, add:

```tsx
        <div className="sidebar-section__header">
          <h2>Groups</h2>
          <button
            className="icon-button"
            type="button"
            aria-label="Create group"
            aria-expanded={isCreatingGroup}
            onClick={() => {
              setIsCreatingGroup((current) => !current);
              setGroupError(null);
            }}
          >
            +
          </button>
        </div>
        {isCreatingGroup ? (
          <form className="sidebar-create-form" onSubmit={handleSubmitGroup}>
            <label>
              <span>Name</span>
              <input
                maxLength={120}
                placeholder="New paper group"
                value={groupName}
                onChange={(event) => setGroupName(event.target.value)}
              />
            </label>
            <label>
              <span>Description</span>
              <textarea
                maxLength={500}
                placeholder="Optional scope note"
                rows={2}
                value={groupDescription}
                onChange={(event) => setGroupDescription(event.target.value)}
              />
            </label>
            {groupError ? <p className="inline-alert inline-alert--error">{groupError}</p> : null}
            <div className="sidebar-create-form__actions">
              <button className="button button--subtle" type="button" onClick={() => setIsCreatingGroup(false)}>
                Cancel
              </button>
              <button className="button button--primary" type="submit" disabled={isSubmittingGroup}>
                {isSubmittingGroup ? "Creating" : "Create"}
              </button>
            </div>
          </form>
        ) : null}
```

- [ ] **Step 7: Pass temporary no-op props from WorkspaceClient**

In `apps/web/components/workspace-client.tsx`, update the `ResearchSidebar` call to pass:

```tsx
          groups={paperGroups}
          activeGroupId={activeGroup?.id ?? ""}
          onSelectGroup={setActiveGroupId}
          onCreateGroup={createGroup}
```

Task 5 defines `activeGroup`, `setActiveGroupId`, and `createGroup`.

- [ ] **Step 8: Run typecheck**

Run:

```powershell
npm --prefix apps/web run typecheck
```

Expected: typecheck may fail until Task 5 defines the WorkspaceClient state. If it fails only for missing `activeGroup`, `setActiveGroupId`, or `createGroup`, continue to Task 5 before committing.

---

### Task 5: WorkspaceClient Active Group State and Layered Views

**Files:**
- Modify: `apps/web/components/workspace-client.tsx`
- Create: `apps/web/components/home-view.tsx`
- Create: `apps/web/components/chat-view.tsx`
- Create: `apps/web/components/paper-manager-view.tsx`

- [ ] **Step 1: Import view type and new components**

In `workspace-client.tsx`, replace the sidebar type import with:

```ts
import { ResearchSidebar } from "@/components/research-sidebar";
import { ChatView } from "@/components/chat-view";
import { HomeView } from "@/components/home-view";
import { PaperManagerView } from "@/components/paper-manager-view";
```

Import `WorkspaceView` from types:

```ts
  WorkspaceView,
```

- [ ] **Step 2: Add active group state**

Change:

```ts
  const [activeView, setActiveView] = useState<WorkspaceView>("research");
```

to:

```ts
  const [activeView, setActiveView] = useState<WorkspaceView>("home");
  const [activeGroupId, setActiveGroupId] = useState("");
```

- [ ] **Step 3: Add active group derivations**

After `activeLibraryGroups`, add:

```ts
  const activeGroup = useMemo(() => {
    return (
      activeLibraryGroups.find((group) => group.id === activeGroupId) ??
      activeLibraryGroups.find((group) => group.name === "Ungrouped uploads") ??
      activeLibraryGroups[0]
    );
  }, [activeGroupId, activeLibraryGroups]);

  const activeGroupPapers = useMemo(() => {
    const paperIds = new Set(activeGroup?.paperIds ?? []);
    return papers.filter((paper) => paperIds.has(paper.id));
  }, [activeGroup?.paperIds, papers]);

  const readyGroupPaperIds = useMemo(
    () => activeGroupPapers.filter((paper) => paper.status === "ready").map((paper) => paper.id),
    [activeGroupPapers]
  );
```

- [ ] **Step 4: Use group scope for chat**

In the `useChatSession` call, replace:

```ts
    readyPaperIds,
```

with:

```ts
    readyPaperIds: readyGroupPaperIds,
```

- [ ] **Step 5: Keep active group valid after workspace load**

After `setActiveLibraryId(nextActiveLibraryId);` in `loadWorkspace`, add:

```ts
      const nextGroups = mappedGroups.filter((group) => group.libraryId === nextActiveLibraryId);
      const nextGroup =
        nextGroups.find((group) => group.id === activeGroupId) ??
        nextGroups.find((group) => group.name === "Ungrouped uploads") ??
        nextGroups[0];
      setActiveGroupId(nextGroup?.id ?? "");
```

- [ ] **Step 6: Update library selection**

In `selectLibrary`, after `setActiveLibraryId(libraryId);`, add:

```ts
    const nextGroups = paperGroups.filter((group) => group.libraryId === libraryId);
    const nextGroup = nextGroups.find((group) => group.name === "Ungrouped uploads") ?? nextGroups[0];
    setActiveGroupId(nextGroup?.id ?? "");
```

- [ ] **Step 7: Add create group handler**

Add this function near `createLibrary`:

```ts
  const createGroup = async (name: string, description: string) => {
    const libraryId = activeLibrary?.id ?? activeLibraryId;
    if (!libraryId) {
      throw new Error("Select a library before creating a group.");
    }

    const created = await paperMemoryApi.createPaperGroup(
      libraryId,
      { name: name.trim(), description: description.trim() },
      installSettings.apiBaseUrl
    );
    const group = mapApiPaperGroup(created);
    setPaperGroups((currentGroups) => [group, ...currentGroups.filter((item) => item.id !== group.id)]);
    setLibraries((currentLibraries) =>
      currentLibraries.map((library) =>
        library.id === libraryId && !library.groupIds.includes(group.id)
          ? { ...library, groupIds: [group.id, ...library.groupIds], updatedAt: group.updatedAt }
          : library
      )
    );
    setActiveGroupId(group.id);
  };
```

- [ ] **Step 8: Add paper move handler**

Add this function near `handleUpload`:

```ts
  const movePaperToGroup = async (paperId: string, groupId: string) => {
    const updated = await paperMemoryApi.movePaperToGroup(groupId, paperId, installSettings.apiBaseUrl);
    const updatedGroup = mapApiPaperGroup(updated);
    setPaperGroups((currentGroups) =>
      currentGroups.map((group) => {
        if (group.id === updatedGroup.id) {
          return updatedGroup;
        }
        if (group.libraryId !== updatedGroup.libraryId || !group.paperIds.includes(paperId)) {
          return group;
        }
        return { ...group, paperIds: group.paperIds.filter((id) => id !== paperId), updatedAt: updatedGroup.updatedAt };
      })
    );
    setLibraries((currentLibraries) =>
      currentLibraries.map((library) =>
        library.id === updatedGroup.libraryId && !library.paperIds.includes(paperId)
          ? { ...library, paperIds: [paperId, ...library.paperIds], updatedAt: updatedGroup.updatedAt }
          : library
      )
    );
  };
```

- [ ] **Step 9: Assign uploads to active group**

In `handleUpload`, after `const uploadedPaper = mapApiPaper(response.paper);`, add:

```ts
      if (activeGroup?.id) {
        await paperMemoryApi.movePaperToGroup(activeGroup.id, uploadedPaper.id, installSettings.apiBaseUrl);
      }
```

Then change the local library paper update so it uses `activeGroup` as the assignment target. The simplest implementation is to keep the existing library patch for compatibility and call `await loadWorkspace({ paperId: uploadedPaper.id, libraryId });` afterward; the reload will pull the updated group state.

- [ ] **Step 10: Create HomeView**

Create `apps/web/components/home-view.tsx`:

```tsx
import type { PaperGroup, PaperSummary, ResearchLibrary, WorkspaceView } from "@/lib/types";

interface HomeViewProps {
  activeLibrary?: ResearchLibrary;
  activeGroup?: PaperGroup;
  papers: PaperSummary[];
  groups: PaperGroup[];
  isPersisted: boolean;
  onViewChange: (view: WorkspaceView) => void;
}

export function HomeView({ activeLibrary, activeGroup, papers, groups, isPersisted, onViewChange }: HomeViewProps) {
  const readyPapers = papers.filter((paper) => paper.status === "ready").length;
  const indexedPages = papers.reduce((total, paper) => total + paper.pages, 0);
  const activeGroupPapers = papers.filter((paper) => activeGroup?.paperIds.includes(paper.id));

  return (
    <section className="home-view" aria-labelledby="home-title">
      <div className="hero-section hero-section--home">
        <div className="hero-section__copy">
          <p className="hero-kicker">Local-first visual RAG for serious reading</p>
          <h1 id="home-title">A research memory organized around paper groups.</h1>
          <p className="hero-section__lead">
            Manage local PDFs by group, then chat with exactly the group you selected.
          </p>
          <div className="hero-actions">
            <button className="button button--primary button--hero" type="button" onClick={() => onViewChange("chat")}>
              Enter Chat
            </button>
            <button className="button button--subtle button--hero" type="button" onClick={() => onViewChange("papers")}>
              Manage Paper Library
            </button>
            <button className="button button--subtle button--hero" type="button" onClick={() => onViewChange("settings")}>
              Settings
            </button>
          </div>
        </div>
        <div className="hero-command" aria-label="Workspace overview">
          <div className="hero-command__top">
            <div>
              <p className="eyebrow">Active group</p>
              <h2>{activeGroup?.name ?? activeLibrary?.name ?? "Research workspace"}</h2>
            </div>
            <span className="hero-command__pill">{isPersisted ? "Local sync" : "Demo mode"}</span>
          </div>
          <div className="hero-metrics">
            <div className="hero-metric"><strong>{readyPapers.toString().padStart(2, "0")}</strong><span>Ready papers</span></div>
            <div className="hero-metric"><strong>{indexedPages.toLocaleString()}</strong><span>Indexed pages</span></div>
            <div className="hero-metric"><strong>{groups.length.toString().padStart(2, "0")}</strong><span>Groups</span></div>
          </div>
          <p className="small-muted">{activeGroupPapers.length} paper(s) are currently in this active RAG group.</p>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 11: Create ChatView**

Create `apps/web/components/chat-view.tsx`:

```tsx
import { ChatPanel } from "@/components/chat-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import type { ApiPageEvidence, ChatMessage, EvidenceItem, PaperGroup, PaperSummary } from "@/lib/types";

interface ChatViewProps {
  activeGroup?: PaperGroup;
  activeGroupPapers: PaperSummary[];
  messages: ChatMessage[];
  question: string;
  isSubmitting: boolean;
  error?: string | null;
  evidence: Array<EvidenceItem | ApiPageEvidence>;
  evidenceNote: string | null;
  paperTitles: Record<string, string>;
  apiBaseUrl: string;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onSearchEvidence: () => void;
}

export function ChatView({
  activeGroup,
  activeGroupPapers,
  messages,
  question,
  isSubmitting,
  error,
  evidence,
  evidenceNote,
  paperTitles,
  apiBaseUrl,
  onQuestionChange,
  onSubmit,
  onReset,
  onSearchEvidence
}: ChatViewProps) {
  const readyCount = activeGroupPapers.filter((paper) => paper.status === "ready").length;
  const pageCount = activeGroupPapers.reduce((total, paper) => total + paper.pages, 0);
  const emptyScopeNote = readyCount === 0 ? "This group has no ready papers yet. Upload and index a PDF before asking paper-grounded questions." : null;

  return (
    <section className="workspace-grid workspace-grid--chat" aria-label="Group scoped chat">
      <div className="workspace-main">
        <section className="panel scope-panel" aria-labelledby="scope-title">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Group RAG scope</p>
              <h2 id="scope-title">Chat with: {activeGroup?.name ?? "No group selected"}</h2>
              <p>{readyCount} ready paper(s), {pageCount} indexed page(s).</p>
            </div>
          </div>
          {emptyScopeNote ? <div className="panel__body"><p className="inline-alert inline-alert--warning">{emptyScopeNote}</p></div> : null}
        </section>
        <ChatPanel
          messages={messages}
          question={question}
          isSubmitting={isSubmitting}
          title={activeGroup ? `Chat with ${activeGroup.name}` : "Research chat"}
          contextLabel="Group-scoped RAG"
          libraryDescription="Questions use only the selected group's ready papers."
          error={error}
          onQuestionChange={onQuestionChange}
          onSubmit={onSubmit}
          onReset={onReset}
          onSearchEvidence={onSearchEvidence}
        />
      </div>
      <aside className="side-stack workspace-aside" aria-label="Retrieved evidence">
        <EvidencePanel evidence={evidence} paperTitles={paperTitles} note={evidenceNote} apiBaseUrl={apiBaseUrl} />
      </aside>
    </section>
  );
}
```

- [ ] **Step 12: Create PaperManagerView**

Create `apps/web/components/paper-manager-view.tsx`:

```tsx
import { PaperLibrary } from "@/components/paper-library";
import { PaperUploadPanel } from "@/components/paper-upload-panel";
import type { PaperGroup, PaperSummary } from "@/lib/types";

interface PaperManagerViewProps {
  activeGroup?: PaperGroup;
  groups: PaperGroup[];
  papers: PaperSummary[];
  uploadTitle: string;
  selectedFile: File | null;
  fileInputKey: number;
  isUploading: boolean;
  uploadMessage: string | null;
  uploadError: string | null;
  onTitleChange: (title: string) => void;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
  onMovePaper: (paperId: string, groupId: string) => Promise<void>;
}

export function PaperManagerView({
  activeGroup,
  groups,
  papers,
  uploadTitle,
  selectedFile,
  fileInputKey,
  isUploading,
  uploadMessage,
  uploadError,
  onTitleChange,
  onFileChange,
  onUpload,
  onMovePaper
}: PaperManagerViewProps) {
  return (
    <section className="workspace-grid workspace-grid--papers" aria-label="Paper manager">
      <div className="workspace-main">
        <section className="panel scope-panel" aria-labelledby="paper-manager-title">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Paper Manager</p>
              <h2 id="paper-manager-title">{activeGroup?.name ?? "No group selected"}</h2>
              <p>Uploads and move actions update this group's RAG scope.</p>
            </div>
          </div>
        </section>
        <PaperUploadPanel
          title={uploadTitle}
          selectedFile={selectedFile}
          fileInputKey={fileInputKey}
          isUploading={isUploading}
          message={uploadMessage}
          error={uploadError}
          onTitleChange={onTitleChange}
          onFileChange={onFileChange}
          onUpload={onUpload}
        />
      </div>
      <aside className="side-stack workspace-aside" aria-label="Papers in active group">
        <PaperLibrary
          papers={papers}
          groups={groups}
          activeGroupId={activeGroup?.id ?? ""}
          onMovePaper={onMovePaper}
        />
      </aside>
    </section>
  );
}
```

- [ ] **Step 13: Replace WorkspaceClient render branch**

Inside `return`, keep `<main className="app-shell">`, render `ResearchSidebar`, then branch:

```tsx
      <section className="workspace-shell" aria-label="PaperMemory workspace">
        <ResearchSidebar ... />
        <div className="workspace-content">
          {activeView === "home" ? (
            <HomeView
              activeLibrary={activeLibrary}
              activeGroup={activeGroup}
              papers={activeLibraryPapers}
              groups={activeLibraryGroups}
              isPersisted={isWorkspacePersisted}
              onViewChange={setActiveView}
            />
          ) : null}
          {activeView === "chat" ? (
            <ChatView
              activeGroup={activeGroup}
              activeGroupPapers={activeGroupPapers}
              messages={messages}
              question={question}
              isSubmitting={isChatSubmitting}
              error={chatError}
              evidence={evidence}
              evidenceNote={evidenceNote}
              paperTitles={paperTitles}
              apiBaseUrl={installSettings.apiBaseUrl}
              onQuestionChange={setQuestion}
              onSubmit={handleSubmitQuestion}
              onReset={resetChat}
              onSearchEvidence={handleSearchEvidence}
            />
          ) : null}
          {activeView === "papers" ? (
            <PaperManagerView
              activeGroup={activeGroup}
              groups={activeLibraryGroups}
              papers={activeGroupPapers}
              uploadTitle={uploadTitle}
              selectedFile={selectedFile}
              fileInputKey={fileInputKey}
              isUploading={isUploading}
              uploadMessage={uploadMessage}
              uploadError={uploadError}
              onTitleChange={setUploadTitle}
              onFileChange={setSelectedFile}
              onUpload={handleUpload}
              onMovePaper={movePaperToGroup}
            />
          ) : null}
          {activeView === "settings" ? (
            <SettingsView
              modelSettings={settings}
              installSettings={installSettings}
              apiDetail={apiStatus.detail}
              onModelSettingsChange={setSettings}
              onInstallSettingsChange={setInstallSettings}
            />
          ) : null}
        </div>
      </section>
```

- [ ] **Step 14: Run typecheck**

Run:

```powershell
npm --prefix apps/web run typecheck
```

Expected: typecheck passes after any import cleanups.

- [ ] **Step 15: Commit layered workspace state**

Run:

```powershell
git -c safe.directory=D:/codex/papermemory add apps/web/components/workspace-client.tsx apps/web/components/home-view.tsx apps/web/components/chat-view.tsx apps/web/components/paper-manager-view.tsx apps/web/components/research-sidebar.tsx
git -c safe.directory=D:/codex/papermemory commit -m "feat(web): add group scoped workspace views"
```

---

### Task 6: Paper Manager Move Controls and Styling

**Files:**
- Modify: `apps/web/components/paper-library.tsx`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Extend PaperLibrary props**

In `paper-library.tsx`, update imports:

```ts
import type { PaperGroup, PaperSummary } from "@/lib/types";
```

Update props:

```ts
interface PaperLibraryProps {
  papers: PaperSummary[];
  embedded?: boolean;
  groups?: PaperGroup[];
  activeGroupId?: string;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
}
```

- [ ] **Step 2: Add move control in cards**

Update `PaperLibraryBody` signature:

```ts
function PaperLibraryBody({
  papers,
  groups = [],
  activeGroupId = "",
  onMovePaper
}: {
  papers: PaperSummary[];
  groups?: PaperGroup[];
  activeGroupId?: string;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
}) {
```

Inside each `.paper-item`, after the summary paragraph, add:

```tsx
            {onMovePaper && groups.length > 0 ? (
              <label className="paper-move-control">
                <span>Move group</span>
                <select
                  value={activeGroupId}
                  onChange={(event) => {
                    const nextGroupId = event.target.value;
                    if (nextGroupId && nextGroupId !== activeGroupId) {
                      void onMovePaper(paper.id, nextGroupId);
                    }
                  }}
                >
                  {groups.map((group) => (
                    <option value={group.id} key={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
```

Pass props through both embedded and non-embedded render paths:

```tsx
<PaperLibraryBody papers={papers} groups={groups} activeGroupId={activeGroupId} onMovePaper={onMovePaper} />
```

- [ ] **Step 3: Add workspace shell styles**

Append these styles to `apps/web/app/globals.css`:

```css
.workspace-shell {
  max-width: 1520px;
  display: grid;
  grid-template-columns: minmax(250px, 0.25fr) minmax(0, 1fr);
  gap: 18px;
  margin: 0 auto;
  padding-top: 18px;
}

.workspace-content {
  min-width: 0;
}

.workspace-grid--chat,
.workspace-grid--papers {
  max-width: none;
}

.home-view {
  min-width: 0;
}

.hero-section--home {
  min-height: calc(100vh - 130px);
  padding-top: 22px;
}

.sidebar-tree-node {
  display: grid;
  gap: 4px;
}

.sidebar-item--group {
  margin-left: 14px;
  grid-template-columns: minmax(0, 1fr) auto;
}

.paper-move-control {
  display: grid;
  gap: 5px;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.paper-move-control select {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.065);
  color: var(--text);
  padding: 8px 10px;
}

.scope-panel .panel__body {
  padding-top: 14px;
}

@media (max-width: 980px) {
  .workspace-shell {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 4: Run frontend typecheck**

Run:

```powershell
npm --prefix apps/web run typecheck
```

Expected: typecheck passes.

- [ ] **Step 5: Commit paper manager controls**

Run:

```powershell
git -c safe.directory=D:/codex/papermemory add apps/web/components/paper-library.tsx apps/web/app/globals.css
git -c safe.directory=D:/codex/papermemory commit -m "feat(web): manage papers by group"
```

---

### Task 7: End-to-End Verification

**Files:**
- No source edits expected unless verification finds a defect.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
$env:PYTHONPATH='D:\codex\papermemory\apps\api;D:\codex\papermemory\apps\api\.venv\Lib\site-packages;D:\codex\papermemory\apps\api\.venv\Lib\site-packages\win32;D:\codex\papermemory\apps\api\.venv\Lib\site-packages\win32\lib'; $env:PATH='D:\codex\papermemory\apps\api\.venv\Lib\site-packages\pywin32_system32;' + $env:PATH; & 'C:\Users\Miles CUI\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend typecheck**

Run:

```powershell
npm --prefix apps/web run typecheck
```

Expected: `tsc --noEmit` exits 0.

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git -c safe.directory=D:/codex/papermemory -c core.whitespace=cr-at-eol diff --check
```

Expected: exit 0.

- [ ] **Step 4: Browser smoke test**

With the existing dev servers running, open `http://127.0.0.1:3000` in the in-app browser and verify:

- Home renders.
- Sidebar shows `Home`, `Chat`, `Paper Manager`, and `Settings`.
- Sidebar shows at least one group under the active library.
- `Paper Manager` opens and shows papers for the active group.
- `Chat` opens and shows `Chat with {group}`.
- Settings still opens.
- Browser console has no error-level logs.

- [ ] **Step 5: Final commit for verification fixes if needed**

If Step 4 required code fixes, commit only those fixes:

```powershell
git -c safe.directory=D:/codex/papermemory add <changed-files>
git -c safe.directory=D:/codex/papermemory commit -m "fix: polish group workspace flow"
```

If no fixes were needed, do not create an empty commit.

---

## Plan Self-Review

Spec coverage:

- `Library -> Group -> Paper`: Tasks 1, 2, 4, 5.
- One paper per group inside a library: Tasks 1 and 2.
- Upload into active group: Task 5.
- Move paper between groups: Tasks 2, 3, 5, 6.
- Home, Chat, Paper Manager, Settings: Tasks 4, 5, 6.
- Group-scoped chat using `paper_ids`: Task 5.
- Repair existing workspace data: Task 1.
- Preserve streaming, multimodal evidence, Markdown, citation navigation, and settings persistence: Tasks 5 and 7 keep existing `useChatSession`, `ChatPanel`, and `SettingsView` behavior.

Red flag scan:

- No banned planning markers or undefined implementation blanks remain.

Type consistency:

- `WorkspaceView` is defined once in `apps/web/lib/types.ts`.
- `PaperGroup.paperIds`, `ResearchLibrary.groupIds`, and `PaperSummary.id` match existing frontend camelCase models.
- Backend route path uses existing `WORKSPACE_ID_PATTERN` and returns existing `PaperGroup`.
