from datetime import UTC, datetime
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.schemas.papers import PaperMetadata, PaperStatus


def _write_ready_paper(storage_root: Path, paper_id: str = "paper-1") -> None:
    paper_dir = storage_root / "papers" / paper_id
    image_dir = storage_root / "rendered_pages" / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    metadata = PaperMetadata(
        paper_id=paper_id,
        title="Visual RAG",
        filename="visrag.pdf",
        status=PaperStatus.ready,
        page_count=1,
        created_at=datetime.now(UTC),
    )
    (paper_dir / "metadata.json").write_text(metadata.model_dump_json(), encoding="utf-8")
    (paper_dir / "source.pdf").write_bytes(b"%PDF-1.7\nfake")
    (image_dir / "page-0001.png").write_bytes(b"\x89PNG\r\n\x1a\nfake-png")


def _client(storage_root: Path) -> TestClient:
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: Settings(
        storage_root=storage_root,
        qdrant_local_path=storage_root / "qdrant-local",
    )
    return TestClient(api)


def test_get_paper_page_image_returns_rendered_png(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path)
    client = _client(tmp_path)

    response = client.get("/papers/paper-1/pages/1/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG\r\n\x1a\nfake-png"


def test_get_paper_page_image_returns_404_for_missing_page(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path)
    client = _client(tmp_path)

    response = client.get("/papers/paper-1/pages/2/image")

    assert response.status_code == 404
    assert response.json()["detail"] == "Page image not found."


def test_get_paper_page_image_rejects_path_traversal_paper_id(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path)
    client = _client(tmp_path)

    response = client.get("/papers/%2e%2e/pages/1/image")

    assert response.status_code == 422


def test_delete_paper_removes_files_and_workspace_references(tmp_path: Path) -> None:
    _write_ready_paper(tmp_path, "paper-delete")
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True)
    now = datetime.now(UTC).isoformat()
    (workspace_dir / "libraries.json").write_text(
        json.dumps(
            [
                {
                    "id": "library-inbox",
                    "name": "Inbox",
                    "description": "",
                    "paper_ids": ["paper-delete"],
                    "group_ids": ["group-inbox"],
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
                    "id": "group-inbox",
                    "library_id": "library-inbox",
                    "name": "Ungrouped uploads",
                    "description": "",
                    "paper_ids": ["paper-delete"],
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        ),
        encoding="utf-8",
    )
    client = _client(tmp_path)

    response = client.delete("/papers/paper-delete")

    assert response.status_code == 204
    assert not (tmp_path / "papers" / "paper-delete").exists()
    assert not (tmp_path / "rendered_pages" / "paper-delete").exists()
    assert client.get("/papers").json() == {"papers": []}
    workspace = client.get("/workspace").json()
    assert workspace["libraries"][0]["paper_ids"] == []
    assert workspace["paper_groups"][0]["paper_ids"] == []


def test_delete_missing_paper_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.delete("/papers/missing-paper")

    assert response.status_code == 404
    assert response.json()["detail"] == "Paper not found."
