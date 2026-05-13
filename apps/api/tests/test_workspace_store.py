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
    assert body["paper_groups"] == []
    assert body["libraries"][0]["group_ids"] == []


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
    assert body["libraries"][0]["group_ids"] == []
    assert body["paper_groups"] == []
