from datetime import UTC, datetime
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.schemas.papers import PaperMetadata, PaperStatus


def _client(storage_root: Path) -> TestClient:
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: Settings(storage_root=storage_root)
    return TestClient(api)


def _write_ready_paper(storage_root: Path, paper_id: str = "paper-1") -> None:
    paper_dir = storage_root / "papers" / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    metadata = PaperMetadata(
        paper_id=paper_id,
        title="VisRAG",
        filename="visrag.pdf",
        status=PaperStatus.ready,
        page_count=3,
        created_at=datetime.now(UTC),
    )
    (paper_dir / "metadata.json").write_text(metadata.model_dump_json(), encoding="utf-8")


def test_workspace_init_creates_default_local_store_and_assigns_existing_papers(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-1")
    client = _client(tmp_path)

    response = client.get("/workspace")

    assert response.status_code == 200
    body = response.json()
    assert body["libraries"][0]["id"] == "library-inbox"
    assert body["libraries"][0]["paper_ids"] == ["paper-1"]
    assert body["paper_groups"][0]["id"] == "group-inbox"
    assert body["paper_groups"][0]["paper_ids"] == ["paper-1"]
    assert body["conversations"][0]["library_id"] == "library-inbox"
    assert (tmp_path / "workspace" / "libraries.json").exists()
    assert (tmp_path / "workspace" / "conversations.json").exists()
    assert (tmp_path / "workspace" / "paper_groups.json").exists()


def test_create_library_persists_to_workspace(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.get("/workspace")

    response = client.post(
        "/workspace/libraries",
        json={"name": "Visual RAG", "description": "Page image papers"},
    )

    assert response.status_code == 201
    library = response.json()
    assert library["name"] == "Visual RAG"
    workspace = client.get("/workspace").json()
    assert any(item["id"] == library["id"] for item in workspace["libraries"])


def test_create_conversation_and_update_messages(tmp_path: Path) -> None:
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]

    created = client.post(
        f"/workspace/libraries/{library_id}/conversations",
        json={"title": "Evidence review", "description": "Scope one database"},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    updated = client.patch(
        f"/workspace/conversations/{conversation_id}",
        json={
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": "What does the paper claim?",
                    "citations": [],
                },
                {
                    "id": "msg-2",
                    "role": "assistant",
                    "content": "It claims page-image evidence is useful.",
                    "citations": [{"paper_id": "paper-1", "label": "VisRAG", "page": 2}],
                },
            ]
        },
    )

    assert updated.status_code == 200
    assert len(updated.json()["messages"]) == 2
    assert updated.json()["messages"][1]["citations"][0]["paper_id"] == "paper-1"


def test_delete_conversation_removes_chat_history_only(tmp_path: Path) -> None:
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]
    created = client.post(
        f"/workspace/libraries/{library_id}/conversations",
        json={
            "title": "Delete this chat",
            "messages": [
                {
                    "id": "msg-delete",
                    "role": "user",
                    "content": "temporary",
                    "citations": [],
                }
            ],
        },
    ).json()

    response = client.delete(f"/workspace/conversations/{created['id']}")

    assert response.status_code == 204
    body = client.get("/workspace").json()
    assert any(library["id"] == library_id for library in body["libraries"])
    assert all(conversation["id"] != created["id"] for conversation in body["conversations"])


def test_delete_missing_conversation_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.get("/workspace")

    response = client.delete("/workspace/conversations/conversation-missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found."


def test_update_library_assigns_paper_ids(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-2")
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]

    response = client.patch(f"/workspace/libraries/{library_id}", json={"paper_ids": ["paper-2", "paper-2"]})

    assert response.status_code == 200
    assert response.json()["paper_ids"] == ["paper-2"]


def test_create_and_update_paper_group(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-3")
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]

    created = client.post(
        f"/workspace/libraries/{library_id}/paper-groups",
        json={"name": "Core papers", "paper_ids": ["paper-3"]},
    )
    assert created.status_code == 201
    group_id = created.json()["id"]

    updated = client.patch(
        f"/workspace/paper-groups/{group_id}",
        json={"description": "Read first", "paper_ids": ["paper-3", "paper-3"]},
    )

    assert updated.status_code == 200
    assert updated.json()["description"] == "Read first"
    assert updated.json()["paper_ids"] == ["paper-3"]

    workspace = client.get("/workspace").json()
    default_group = next(group for group in workspace["paper_groups"] if group["id"] == "group-inbox")
    custom_group = next(group for group in workspace["paper_groups"] if group["id"] == group_id)
    assert default_group["paper_ids"] == []
    assert custom_group["paper_ids"] == ["paper-3"]


def test_assign_new_paper_to_custom_library_does_not_add_it_to_inbox(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-old")
    client = _client(tmp_path)
    client.get("/workspace")

    custom = client.post("/workspace/libraries", json={"name": "Custom database"}).json()
    _write_ready_paper(tmp_path, "paper-new")

    response = client.patch(
        f"/workspace/libraries/{custom['id']}",
        json={"paper_ids": ["paper-new"]},
    )

    assert response.status_code == 200
    workspace = client.get("/workspace").json()
    inbox = next(library for library in workspace["libraries"] if library["id"] == "library-inbox")
    custom_library = next(library for library in workspace["libraries"] if library["id"] == custom["id"])
    assert "paper-new" not in inbox["paper_ids"]
    assert custom_library["paper_ids"] == ["paper-new"]


def test_update_library_rejects_unknown_paper_id(tmp_path: Path) -> None:
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]

    response = client.patch(f"/workspace/libraries/{library_id}", json={"paper_ids": ["missing-paper"]})

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown paper id: missing-paper"


def test_update_library_rejects_group_from_another_library(tmp_path: Path) -> None:
    client = _client(tmp_path)
    first_library_id = client.get("/workspace").json()["libraries"][0]["id"]
    second_library = client.post("/workspace/libraries", json={"name": "Second"}).json()
    group = client.post(
        f"/workspace/libraries/{second_library['id']}/paper-groups",
        json={"name": "Second group"},
    ).json()

    response = client.patch(f"/workspace/libraries/{first_library_id}", json={"group_ids": [group["id"]]})

    assert response.status_code == 400
    assert response.json()["detail"] == "Paper group does not belong to this library."


def test_create_paper_group_rejects_paper_outside_library(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-outside")
    client = _client(tmp_path)
    library = client.post("/workspace/libraries", json={"name": "Empty library"}).json()

    response = client.post(
        f"/workspace/libraries/{library['id']}/paper-groups",
        json={"name": "Invalid group", "paper_ids": ["paper-outside"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Paper group paper_ids must already belong to the same library."


def test_ensure_defaults_preserves_existing_libraries_when_other_files_are_missing(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True)
    now = datetime.now(UTC).isoformat()
    existing_libraries = [
        {
            "id": "library-custom",
            "name": "Preserve me",
            "description": "Existing data",
            "paper_ids": [],
            "group_ids": [],
            "created_at": now,
            "updated_at": now,
        }
    ]
    (workspace_dir / "libraries.json").write_text(json.dumps(existing_libraries), encoding="utf-8")
    client = _client(tmp_path)

    response = client.get("/workspace")

    assert response.status_code == 200
    body = response.json()
    assert len(body["libraries"]) == 1
    assert body["libraries"][0]["id"] == "library-custom"
    assert body["libraries"][0]["name"] == "Preserve me"
    assert body["conversations"][0]["library_id"] == "library-custom"
    assert len(body["paper_groups"]) == 1
    group = body["paper_groups"][0]
    assert group["library_id"] == "library-custom"
    assert group["name"] == "Ungrouped uploads"
    assert group["paper_ids"] == []
    assert body["libraries"][0]["group_ids"] == [group["id"]]


def test_ensure_defaults_repairs_missing_paper_groups_without_unreferenced_groups(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True)
    now = datetime.now(UTC).isoformat()
    existing_libraries = [
        {
            "id": "library-custom",
            "name": "Preserve me",
            "description": "Existing data",
            "paper_ids": [],
            "group_ids": ["group-missing"],
            "created_at": now,
            "updated_at": now,
        }
    ]
    (workspace_dir / "libraries.json").write_text(json.dumps(existing_libraries), encoding="utf-8")
    (workspace_dir / "conversations.json").write_text("[]", encoding="utf-8")
    client = _client(tmp_path)

    response = client.get("/workspace")

    assert response.status_code == 200
    body = response.json()
    assert len(body["libraries"]) == 1
    assert body["libraries"][0]["id"] == "library-custom"
    assert body["libraries"][0]["name"] == "Preserve me"
    assert len(body["paper_groups"]) == 1
    group = body["paper_groups"][0]
    assert group["library_id"] == "library-custom"
    assert group["name"] == "Ungrouped uploads"
    assert group["paper_ids"] == []
    assert body["libraries"][0]["group_ids"] == [group["id"]]


def test_workspace_repair_creates_default_group_for_empty_library_without_groups(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True)
    now = datetime.now(UTC).isoformat()
    (workspace_dir / "libraries.json").write_text(
        json.dumps(
            [
                {
                    "id": "library-empty",
                    "name": "Empty",
                    "description": "",
                    "paper_ids": [],
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
    assert library["id"] == "library-empty"
    assert len(body["paper_groups"]) == 1
    group = body["paper_groups"][0]
    assert group["library_id"] == "library-empty"
    assert group["name"] == "Ungrouped uploads"
    assert group["paper_ids"] == []
    assert library["group_ids"] == [group["id"]]


def test_workspace_repair_rebuilds_library_group_ids_in_repaired_group_order(tmp_path: Path) -> None:
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
                    "paper_ids": [],
                    "group_ids": ["group-second", "group-first"],
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
                    "id": "group-first",
                    "library_id": "library-custom",
                    "name": "First",
                    "description": "",
                    "paper_ids": [],
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "group-second",
                    "library_id": "library-custom",
                    "name": "Second",
                    "description": "",
                    "paper_ids": [],
                    "created_at": now,
                    "updated_at": now,
                },
            ]
        ),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    body = client.get("/workspace").json()

    assert [group["id"] for group in body["paper_groups"]] == ["group-first", "group-second"]
    assert body["libraries"][0]["group_ids"] == ["group-first", "group-second"]


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


def test_workspace_repair_assigns_orphan_papers_to_new_default_group_without_polluting_custom_group(
    tmp_path: Path,
) -> None:
    _write_ready_paper(tmp_path, "paper-owned")
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
                    "paper_ids": ["paper-owned", "paper-orphan"],
                    "group_ids": ["group-custom"],
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
                    "id": "group-custom",
                    "library_id": "library-custom",
                    "name": "Custom group",
                    "description": "",
                    "paper_ids": ["paper-owned"],
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        ),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    body = client.get("/workspace").json()

    groups = body["paper_groups"]
    custom_group = next(group for group in groups if group["id"] == "group-custom")
    default_group = next(group for group in groups if group["name"] == "Ungrouped uploads")
    assert custom_group["paper_ids"] == ["paper-owned"]
    assert default_group["paper_ids"] == ["paper-orphan"]
    assert body["libraries"][0]["group_ids"] == [group["id"] for group in groups]


def test_workspace_repair_assigns_orphan_papers_to_existing_default_group(tmp_path: Path) -> None:
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
                    "group_ids": ["group-default"],
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
                    "id": "group-default",
                    "library_id": "library-custom",
                    "name": "Ungrouped uploads",
                    "description": "",
                    "paper_ids": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        ),
        encoding="utf-8",
    )

    client = _client(tmp_path)
    body = client.get("/workspace").json()

    group = body["paper_groups"][0]
    assert group["id"] == "group-default"
    assert group["paper_ids"] == ["paper-orphan"]


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


def test_delete_library_removes_workspace_scope_without_deleting_paper_files(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-keep")
    client = _client(tmp_path)
    client.get("/workspace")
    library = client.post("/workspace/libraries", json={"name": "Temporary library"}).json()
    client.patch(f"/workspace/libraries/{library['id']}", json={"paper_ids": ["paper-keep"]})
    group = client.post(
        f"/workspace/libraries/{library['id']}/paper-groups",
        json={"name": "Temporary group", "paper_ids": ["paper-keep"]},
    ).json()
    conversation = client.post(
        f"/workspace/libraries/{library['id']}/conversations",
        json={"title": "Temporary chat"},
    ).json()

    response = client.delete(f"/workspace/libraries/{library['id']}")

    assert response.status_code == 204
    body = client.get("/workspace").json()
    assert all(item["id"] != library["id"] for item in body["libraries"])
    assert all(item["id"] != group["id"] for item in body["paper_groups"])
    assert all(item["id"] != conversation["id"] for item in body["conversations"])
    assert (tmp_path / "papers" / "paper-keep" / "metadata.json").exists()


def test_delete_last_library_returns_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]

    response = client.delete(f"/workspace/libraries/{library_id}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete the last library."


def test_delete_paper_group_moves_papers_to_default_group(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-move")
    client = _client(tmp_path)
    library_id = client.get("/workspace").json()["libraries"][0]["id"]
    custom_group = client.post(
        f"/workspace/libraries/{library_id}/paper-groups",
        json={"name": "Delete me", "paper_ids": ["paper-move"]},
    ).json()

    response = client.delete(f"/workspace/paper-groups/{custom_group['id']}")

    assert response.status_code == 204
    groups = client.get("/workspace").json()["paper_groups"]
    assert all(group["id"] != custom_group["id"] for group in groups)
    default_group = next(group for group in groups if group["name"] == "Ungrouped uploads")
    assert default_group["paper_ids"] == ["paper-move"]


def test_delete_default_or_last_paper_group_returns_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = client.get("/workspace").json()
    default_group = next(group for group in body["paper_groups"] if group["name"] == "Ungrouped uploads")

    last_group_response = client.delete(f"/workspace/paper-groups/{default_group['id']}")

    assert last_group_response.status_code == 400
    assert last_group_response.json()["detail"] == "Cannot delete the last paper group in a library."

    library_id = body["libraries"][0]["id"]
    client.post(f"/workspace/libraries/{library_id}/paper-groups", json={"name": "Other group"})

    default_group_response = client.delete(f"/workspace/paper-groups/{default_group['id']}")

    assert default_group_response.status_code == 400
    assert default_group_response.json()["detail"] == "Cannot delete the default ungrouped uploads group."
