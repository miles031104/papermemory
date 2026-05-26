from fastapi import APIRouter, Depends, Path

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
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
    WORKSPACE_ID_PATTERN,
    WorkspaceResponse,
)
from app.services.workspace_store import WorkspaceStore

router = APIRouter()


def get_workspace_store(settings: Settings = Depends(get_settings)) -> WorkspaceStore:
    return WorkspaceStore(paths=StoragePaths(settings))


@router.get("", response_model=WorkspaceResponse)
def get_workspace(store: WorkspaceStore = Depends(get_workspace_store)) -> WorkspaceResponse:
    return store.get_workspace()


@router.post("/libraries", response_model=ResearchLibrary, status_code=201)
def create_library(
    request: CreateLibraryRequest,
    store: WorkspaceStore = Depends(get_workspace_store),
) -> ResearchLibrary:
    return store.create_library(request)


@router.patch("/libraries/{library_id}", response_model=ResearchLibrary)
def update_library(
    request: UpdateLibraryRequest,
    library_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> ResearchLibrary:
    return store.update_library(library_id=library_id, request=request)


@router.delete("/libraries/{library_id}", status_code=204)
def delete_library(
    library_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> None:
    store.delete_library(library_id=library_id)


@router.post("/libraries/{library_id}/conversations", response_model=ResearchConversation, status_code=201)
def create_conversation(
    request: CreateConversationRequest,
    library_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> ResearchConversation:
    return store.create_conversation(library_id=library_id, request=request)


@router.patch("/conversations/{conversation_id}", response_model=ResearchConversation)
def update_conversation(
    request: UpdateConversationRequest,
    conversation_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> ResearchConversation:
    return store.update_conversation(conversation_id=conversation_id, request=request)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> None:
    store.delete_conversation(conversation_id=conversation_id)


@router.post("/libraries/{library_id}/paper-groups", response_model=PaperGroup, status_code=201)
def create_paper_group(
    request: CreatePaperGroupRequest,
    library_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> PaperGroup:
    return store.create_paper_group(library_id=library_id, request=request)


@router.patch("/paper-groups/{group_id}", response_model=PaperGroup)
def update_paper_group(
    request: UpdatePaperGroupRequest,
    group_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> PaperGroup:
    return store.update_paper_group(group_id=group_id, request=request)


@router.delete("/paper-groups/{group_id}", status_code=204)
def delete_paper_group(
    group_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> None:
    store.delete_paper_group(group_id=group_id)


@router.post("/paper-groups/{group_id}/papers/{paper_id}", response_model=PaperGroup)
def move_paper_to_group(
    group_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    paper_id: str = Path(pattern=WORKSPACE_ID_PATTERN),
    store: WorkspaceStore = Depends(get_workspace_store),
) -> PaperGroup:
    return store.move_paper_to_group(group_id=group_id, paper_id=paper_id)
