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
