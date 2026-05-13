from datetime import UTC, datetime
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
    (image_dir / "page-0001.png").write_bytes(b"\x89PNG\r\n\x1a\nfake-png")


def _client(storage_root: Path) -> TestClient:
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: Settings(storage_root=storage_root)
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
