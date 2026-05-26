from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.core.paths import StoragePaths
from app.schemas.papers import PaperMetadata
from app.schemas.workspace import (
    CreateConversationRequest,
    CreateLibraryRequest,
    CreatePaperGroupRequest,
    PaperGroup,
    ResearchConversation,
    ResearchLibrary,
    UpdateConversationRequest,
    UpdateLibraryRequest,
    UpdatePaperGroupRequest,
    WorkspaceResponse,
    is_safe_workspace_id,
)


DEFAULT_LIBRARY_ID = "library-inbox"
DEFAULT_GROUP_ID = "group-inbox"
DEFAULT_CONVERSATION_ID = "conversation-welcome"
DEFAULT_GROUP_NAME = "Ungrouped uploads"
DEFAULT_GROUP_DESCRIPTION = "Default local-first group for papers that have not been organized yet."


class WorkspaceStore:
    """Local JSON persistence for research libraries, conversations, and paper groups."""

    def __init__(self, paths: StoragePaths) -> None:
        self.paths = paths
        self._defaults_initialized: bool = False
        self.paths.ensure_all()

    @property
    def libraries_path(self) -> Path:
        return self.paths.workspace_dir / "libraries.json"

    @property
    def conversations_path(self) -> Path:
        return self.paths.workspace_dir / "conversations.json"

    @property
    def paper_groups_path(self) -> Path:
        return self.paths.workspace_dir / "paper_groups.json"

    def get_workspace(self) -> WorkspaceResponse:
        return self._load_workspace()

    def create_library(self, request: CreateLibraryRequest) -> ResearchLibrary:
        workspace = self._load_workspace()
        paper_ids = self._validate_existing_paper_ids(request.paper_ids)
        now = self._now()
        library = ResearchLibrary(
            id=self._new_id("library"),
            name=request.name.strip(),
            description=request.description,
            paper_ids=paper_ids,
            group_ids=[],
            created_at=now,
            updated_at=now,
        )
        workspace.libraries.append(library)
        self._write_workspace(workspace)
        return library

    def update_library(self, library_id: str, request: UpdateLibraryRequest) -> ResearchLibrary:
        self._validate_id(library_id, "Invalid library id.")
        workspace = self._load_workspace()
        index, library = self._find_library(workspace, library_id)
        changes: dict[str, object] = {}
        if request.name is not None:
            changes["name"] = request.name
        if request.description is not None:
            changes["description"] = request.description
        next_paper_ids = request.paper_ids if request.paper_ids is not None else library.paper_ids
        next_group_ids = request.group_ids if request.group_ids is not None else library.group_ids
        validated_paper_ids = self._validate_existing_paper_ids(next_paper_ids)
        validated_group_ids = self._validate_group_ids_for_library(
            workspace=workspace,
            library_id=library_id,
            group_ids=next_group_ids,
        )
        self._validate_library_group_papers(
            workspace=workspace,
            library_id=library_id,
            paper_ids=validated_paper_ids,
        )
        updated = library.model_copy(
            update={
                **changes,
                "paper_ids": validated_paper_ids,
                "group_ids": validated_group_ids,
                "updated_at": self._now(),
            }
        )
        workspace.libraries[index] = updated
        self._write_workspace(workspace)
        return updated

    def create_conversation(
        self,
        library_id: str,
        request: CreateConversationRequest,
    ) -> ResearchConversation:
        self._validate_id(library_id, "Invalid library id.")
        workspace = self._load_workspace()
        self._find_library(workspace, library_id)
        now = self._now()
        conversation = ResearchConversation(
            id=self._new_id("conversation"),
            library_id=library_id,
            title=request.title.strip(),
            description=request.description,
            messages=request.messages,
            created_at=now,
            updated_at=now,
        )
        workspace.conversations.insert(0, conversation)
        self._write_workspace(workspace)
        return conversation

    def update_conversation(
        self,
        conversation_id: str,
        request: UpdateConversationRequest,
    ) -> ResearchConversation:
        self._validate_id(conversation_id, "Invalid conversation id.")
        workspace = self._load_workspace()
        index, conversation = self._find_conversation(workspace, conversation_id)
        changes: dict[str, object] = {}
        if request.title is not None:
            changes["title"] = request.title
        if request.description is not None:
            changes["description"] = request.description
        if request.messages is not None:
            changes["messages"] = request.messages
        updated = conversation.model_copy(update={**changes, "updated_at": self._now()})
        workspace.conversations[index] = updated
        self._write_workspace(workspace)
        return updated

    def create_paper_group(self, library_id: str, request: CreatePaperGroupRequest) -> PaperGroup:
        self._validate_id(library_id, "Invalid library id.")
        workspace = self._load_workspace()
        library_index, library = self._find_library(workspace, library_id)
        paper_ids = self._validate_group_paper_ids(
            workspace=workspace,
            library_id=library_id,
            paper_ids=request.paper_ids,
        )
        now = self._now()
        group = PaperGroup(
            id=self._new_id("group"),
            library_id=library_id,
            name=request.name.strip(),
            description=request.description,
            paper_ids=paper_ids,
            created_at=now,
            updated_at=now,
        )
        workspace.paper_groups.append(group)
        workspace.libraries[library_index] = library.model_copy(
            update={"group_ids": self._dedupe([*library.group_ids, group.id]), "updated_at": now}
        )
        self._remove_paper_ids_from_other_groups(
            workspace=workspace,
            library_id=library_id,
            keeper_group_id=group.id,
            paper_ids=paper_ids,
            now=now,
        )
        self._write_workspace(workspace)
        return group

    def update_paper_group(self, group_id: str, request: UpdatePaperGroupRequest) -> PaperGroup:
        self._validate_id(group_id, "Invalid paper group id.")
        workspace = self._load_workspace()
        index, group = self._find_paper_group(workspace, group_id)
        changes: dict[str, object] = {}
        if request.name is not None:
            changes["name"] = request.name
        if request.description is not None:
            changes["description"] = request.description
        next_paper_ids = request.paper_ids if request.paper_ids is not None else group.paper_ids
        validated_paper_ids = self._validate_group_paper_ids(
            workspace=workspace,
            library_id=group.library_id,
            paper_ids=next_paper_ids,
        )
        updated = group.model_copy(
            update={
                **changes,
                "paper_ids": validated_paper_ids,
                "updated_at": self._now(),
            }
        )
        workspace.paper_groups[index] = updated
        self._remove_paper_ids_from_other_groups(
            workspace=workspace,
            library_id=group.library_id,
            keeper_group_id=group.id,
            paper_ids=validated_paper_ids,
            now=updated.updated_at,
        )
        self._write_workspace(workspace)
        return updated

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

    def _ensure_defaults(self) -> None:
        now = self._now()
        existing_libraries = self._read_list(self.libraries_path, ResearchLibrary) if self.libraries_path.exists() else []
        default_library_id = existing_libraries[0].id if existing_libraries else DEFAULT_LIBRARY_ID
        existing_paper_ids = self._existing_paper_ids() if not self.libraries_path.exists() else []
        library = ResearchLibrary(
            id=DEFAULT_LIBRARY_ID,
            name="Inbox",
            description="Fresh local PDF uploads before they are organized into research databases.",
            paper_ids=existing_paper_ids,
            group_ids=[DEFAULT_GROUP_ID],
            created_at=now,
            updated_at=now,
        )
        group = PaperGroup(
            id=DEFAULT_GROUP_ID,
            library_id=default_library_id,
            name=DEFAULT_GROUP_NAME,
            description=DEFAULT_GROUP_DESCRIPTION,
            paper_ids=existing_paper_ids,
            created_at=now,
            updated_at=now,
        )
        conversation = ResearchConversation(
            id=DEFAULT_CONVERSATION_ID,
            library_id=default_library_id,
            title="Research chat",
            description="Ask questions over the active local paper database.",
            messages=[],
            created_at=now,
            updated_at=now,
        )
        if not self.libraries_path.exists():
            self._atomic_write_json(self.libraries_path, [library.model_dump(mode="json")])
        if not self.paper_groups_path.exists():
            if existing_libraries:
                repaired_libraries = [
                    item.model_copy(update={"group_ids": [], "updated_at": now}) if item.group_ids else item
                    for item in existing_libraries
                ]
                if repaired_libraries != existing_libraries:
                    self._atomic_write_json(
                        self.libraries_path,
                        [item.model_dump(mode="json") for item in repaired_libraries],
                    )
                self._atomic_write_json(self.paper_groups_path, [])
            else:
                self._atomic_write_json(self.paper_groups_path, [group.model_dump(mode="json")])
        if not self.conversations_path.exists():
            self._atomic_write_json(self.conversations_path, [conversation.model_dump(mode="json")])

    def _repair_empty_workspace(self) -> WorkspaceResponse:
        existing_paper_ids = self._existing_paper_ids()
        now = self._now()
        workspace = WorkspaceResponse(
            libraries=[
                ResearchLibrary(
                    id=DEFAULT_LIBRARY_ID,
                    name="Inbox",
                    description="Fresh local PDF uploads before they are organized into research databases.",
                    paper_ids=existing_paper_ids,
                    group_ids=[DEFAULT_GROUP_ID],
                    created_at=now,
                    updated_at=now,
                )
            ],
            conversations=[
                ResearchConversation(
                    id=DEFAULT_CONVERSATION_ID,
                    library_id=DEFAULT_LIBRARY_ID,
                    title="Research chat",
                    description="Ask questions over the active local paper database.",
                    messages=[],
                    created_at=now,
                    updated_at=now,
                )
            ],
            paper_groups=[
                PaperGroup(
                    id=DEFAULT_GROUP_ID,
                    library_id=DEFAULT_LIBRARY_ID,
                    name=DEFAULT_GROUP_NAME,
                    description=DEFAULT_GROUP_DESCRIPTION,
                    paper_ids=existing_paper_ids,
                    created_at=now,
                    updated_at=now,
                )
            ],
        )
        self._write_workspace(workspace)
        return workspace

    def _repair_workspace_integrity(self, workspace: WorkspaceResponse) -> WorkspaceResponse:
        now = self._now()
        changed = False
        repaired_groups: list[PaperGroup] = []

        libraries_by_id = {library.id: library for library in workspace.libraries}
        library_group_ids: dict[str, list[str]] = {library.id: [] for library in workspace.libraries}
        assigned_papers_by_library: dict[str, set[str]] = {library.id: set() for library in workspace.libraries}

        for group in workspace.paper_groups:
            library = libraries_by_id.get(group.library_id)
            if library is None:
                changed = True
                continue

            library_paper_ids = set(library.paper_ids)
            assigned_paper_ids = assigned_papers_by_library[group.library_id]
            repaired_paper_ids: list[str] = []
            for paper_id in self._dedupe(group.paper_ids):
                if paper_id not in library_paper_ids or paper_id in assigned_paper_ids:
                    changed = True
                    continue
                repaired_paper_ids.append(paper_id)
                assigned_paper_ids.add(paper_id)

            if repaired_paper_ids != group.paper_ids:
                group = group.model_copy(update={"paper_ids": repaired_paper_ids, "updated_at": now})
                changed = True
            repaired_groups.append(group)
            library_group_ids[group.library_id].append(group.id)

        for library in workspace.libraries:
            ungrouped_paper_ids = [
                paper_id for paper_id in library.paper_ids if paper_id not in assigned_papers_by_library[library.id]
            ]
            if not ungrouped_paper_ids and library_group_ids[library.id]:
                continue

            target_group_id = None
            if library_group_ids[library.id]:
                default_group = next(
                    (
                        group
                        for group in repaired_groups
                        if group.library_id == library.id and group.name == DEFAULT_GROUP_NAME
                    ),
                    None,
                )
                target_group_id = default_group.id if default_group is not None else None

            if target_group_id is None:
                default_group = self._default_group_for_library(
                    library=library,
                    existing_group_ids={group.id for group in repaired_groups},
                    paper_ids=ungrouped_paper_ids,
                    now=now,
                )
                repaired_groups.append(default_group)
                library_group_ids[library.id].append(default_group.id)
            elif ungrouped_paper_ids:
                repaired_groups = [
                    group.model_copy(
                        update={
                            "paper_ids": self._dedupe([*group.paper_ids, *ungrouped_paper_ids]),
                            "updated_at": now,
                        }
                    )
                    if group.id == target_group_id
                    else group
                    for group in repaired_groups
                ]
            assigned_papers_by_library[library.id].update(ungrouped_paper_ids)
            changed = True

        repaired_libraries: list[ResearchLibrary] = []
        for library in workspace.libraries:
            repaired_group_ids = self._dedupe(library_group_ids[library.id])
            if repaired_group_ids != library.group_ids:
                library = library.model_copy(update={"group_ids": repaired_group_ids, "updated_at": now})
                changed = True
            repaired_libraries.append(library)

        if not changed:
            return workspace

        repaired = workspace.model_copy(update={"libraries": repaired_libraries, "paper_groups": repaired_groups})
        self._write_workspace(repaired)
        return repaired

    def _default_group_for_library(
        self,
        library: ResearchLibrary,
        existing_group_ids: set[str],
        paper_ids: list[str],
        now: datetime,
    ) -> PaperGroup:
        group_id = f"group-{library.id}"
        if group_id in existing_group_ids:
            group_id = self._new_id("group")
        return PaperGroup(
            id=group_id,
            library_id=library.id,
            name=DEFAULT_GROUP_NAME,
            description=DEFAULT_GROUP_DESCRIPTION,
            paper_ids=paper_ids,
            created_at=now,
            updated_at=now,
        )

    def _write_workspace(self, workspace: WorkspaceResponse) -> None:
        self._atomic_write_json(
            self.libraries_path,
            [library.model_dump(mode="json") for library in workspace.libraries],
        )
        self._atomic_write_json(
            self.conversations_path,
            [conversation.model_dump(mode="json") for conversation in workspace.conversations],
        )
        self._atomic_write_json(
            self.paper_groups_path,
            [group.model_dump(mode="json") for group in workspace.paper_groups],
        )

    def _read_list(self, path: Path, model: type[ResearchLibrary] | type[ResearchConversation] | type[PaperGroup]):
        if not path.exists():
            return []
        try:
            raw_items = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Invalid workspace store file: {path.name}") from exc
        if not isinstance(raw_items, list):
            raise HTTPException(status_code=500, detail=f"Workspace store file must contain a list: {path.name}")
        return [model.model_validate(item) for item in raw_items]

    def _existing_paper_ids(self) -> list[str]:
        paper_ids: list[str] = []
        for metadata_path in sorted(self.paths.papers_dir.glob("*/metadata.json")):
            try:
                metadata = PaperMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            paper_ids.append(metadata.paper_id)
        return paper_ids

    def _validate_existing_paper_ids(self, paper_ids: list[str]) -> list[str]:
        deduped_paper_ids = self._dedupe(paper_ids)
        existing_paper_ids = set(self._existing_paper_ids())
        missing_paper_ids = [paper_id for paper_id in deduped_paper_ids if paper_id not in existing_paper_ids]
        if missing_paper_ids:
            raise HTTPException(status_code=400, detail=f"Unknown paper id: {missing_paper_ids[0]}")
        return deduped_paper_ids

    def _validate_group_ids_for_library(
        self,
        workspace: WorkspaceResponse,
        library_id: str,
        group_ids: list[str],
    ) -> list[str]:
        deduped_group_ids = self._dedupe(group_ids)
        groups_by_id = {group.id: group for group in workspace.paper_groups}
        for group_id in deduped_group_ids:
            group = groups_by_id.get(group_id)
            if group is None:
                raise HTTPException(status_code=400, detail=f"Unknown paper group id: {group_id}")
            if group.library_id != library_id:
                raise HTTPException(status_code=400, detail="Paper group does not belong to this library.")
        return deduped_group_ids

    def _validate_group_paper_ids(
        self,
        workspace: WorkspaceResponse,
        library_id: str,
        paper_ids: list[str],
    ) -> list[str]:
        deduped_paper_ids = self._validate_existing_paper_ids(paper_ids)
        _, library = self._find_library(workspace, library_id)
        library_paper_ids = set(library.paper_ids)
        for paper_id in deduped_paper_ids:
            if paper_id not in library_paper_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Paper group paper_ids must already belong to the same library.",
                )
        return deduped_paper_ids

    def _validate_library_group_papers(
        self,
        workspace: WorkspaceResponse,
        library_id: str,
        paper_ids: list[str],
    ) -> None:
        library_paper_ids = set(paper_ids)
        for group in workspace.paper_groups:
            if group.library_id != library_id:
                continue
            for group_paper_id in group.paper_ids:
                if group_paper_id not in library_paper_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Library paper_ids cannot remove papers that are still used by a paper group.",
                    )

    def _remove_paper_ids_from_other_groups(
        self,
        workspace: WorkspaceResponse,
        library_id: str,
        keeper_group_id: str,
        paper_ids: list[str],
        now: datetime,
    ) -> None:
        if not paper_ids:
            return

        paper_id_set = set(paper_ids)
        for index, group in enumerate(workspace.paper_groups):
            if group.library_id != library_id or group.id == keeper_group_id:
                continue

            next_paper_ids = [paper_id for paper_id in group.paper_ids if paper_id not in paper_id_set]
            if next_paper_ids != group.paper_ids:
                workspace.paper_groups[index] = group.model_copy(
                    update={"paper_ids": next_paper_ids, "updated_at": now}
                )

    def _atomic_write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.{uuid4().hex}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        temp_path.replace(path)

    def _find_library(self, workspace: WorkspaceResponse, library_id: str) -> tuple[int, ResearchLibrary]:
        for index, library in enumerate(workspace.libraries):
            if library.id == library_id:
                return index, library
        raise HTTPException(status_code=404, detail="Library not found.")

    def _find_conversation(self, workspace: WorkspaceResponse, conversation_id: str) -> tuple[int, ResearchConversation]:
        for index, conversation in enumerate(workspace.conversations):
            if conversation.id == conversation_id:
                return index, conversation
        raise HTTPException(status_code=404, detail="Conversation not found.")

    def _find_paper_group(self, workspace: WorkspaceResponse, group_id: str) -> tuple[int, PaperGroup]:
        for index, group in enumerate(workspace.paper_groups):
            if group.id == group_id:
                return index, group
        raise HTTPException(status_code=404, detail="Paper group not found.")

    def _validate_id(self, value: str, detail: str) -> None:
        if not is_safe_workspace_id(value):
            raise HTTPException(status_code=400, detail=detail)

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _dedupe(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
