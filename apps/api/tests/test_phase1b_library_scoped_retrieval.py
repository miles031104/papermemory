import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.main import create_app
from app.routers import papers, retrieval
from app.services.indexing_service import IndexingService
from app.services.ingestion_service import IngestionService
from app.services.pdf_renderer import PdfRenderer
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService


def _minimal_pdf_bytes(label: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page(width=320, height=180)
    page.insert_text((36, 72), label, fontsize=12)
    payload = document.tobytes()
    document.close()
    assert payload.startswith(b"%PDF")
    return payload


async def _close_qdrant_client(store: VectorStore) -> None:
    close = getattr(store.client, "close", None)
    if close is None:
        return
    result = close()
    if hasattr(result, "__await__"):
        await result


def test_uploaded_ready_paper_is_retrieved_only_inside_active_library_scope(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        qdrant_mode="local",
        qdrant_local_path=tmp_path / "qdrant-local",
        qdrant_collection="phase1b_library_scoped_retrieval",
        qdrant_vector_size=8,
        visrag_backend="stub",
        max_pdf_pages=5,
        pdf_render_zoom=1.0,
    )
    visrag = VisRAGService(settings=settings)
    vector_store = VectorStore(settings=settings)
    ingestion_service = IngestionService(
        paths=StoragePaths(settings),
        renderer=PdfRenderer(
            zoom=settings.pdf_render_zoom,
            max_pages=settings.max_pdf_pages,
        ),
        indexing_service=IndexingService(
            visrag=visrag,
            vector_store=vector_store,
        ),
        max_upload_bytes=settings.max_upload_bytes,
    )

    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[papers.get_ingestion_service] = lambda: ingestion_service
    api.dependency_overrides[retrieval.get_visrag_service] = lambda: visrag
    api.dependency_overrides[retrieval.get_vector_store] = lambda: vector_store

    try:
        with TestClient(api) as client:
            workspace = client.get("/workspace")
            assert workspace.status_code == 200

            library_a = client.post(
                "/workspace/libraries",
                json={"name": "Scoped Library A", "description": "Active search scope"},
            )
            library_b = client.post(
                "/workspace/libraries",
                json={"name": "Scoped Library B", "description": "Different search scope"},
            )
            empty_library = client.post(
                "/workspace/libraries",
                json={"name": "Empty Library", "description": "No ready papers yet"},
            )
            assert library_a.status_code == 201
            assert library_b.status_code == 201
            assert empty_library.status_code == 201
            library_a_id = library_a.json()["id"]
            library_b_id = library_b.json()["id"]

            upload_a = client.post(
                "/papers/upload",
                data={"title": "Phase 1B Paper A"},
                files={
                    "file": (
                        "phase1b-a.pdf",
                        _minimal_pdf_bytes("Phase 1B scoped evidence paper A"),
                        "application/pdf",
                    )
                },
            )
            upload_b = client.post(
                "/papers/upload",
                data={"title": "Phase 1B Paper B"},
                files={
                    "file": (
                        "phase1b-b.pdf",
                        _minimal_pdf_bytes("Phase 1B scoped evidence paper B"),
                        "application/pdf",
                    )
                },
            )
            assert upload_a.status_code == 201
            assert upload_b.status_code == 201
            paper_a = upload_a.json()["paper"]
            paper_b = upload_b.json()["paper"]
            assert paper_a["status"] == "ready"
            assert paper_b["status"] == "ready"

            patch_a = client.patch(
                f"/workspace/libraries/{library_a_id}",
                json={"paper_ids": [paper_a["paper_id"]]},
            )
            patch_b = client.patch(
                f"/workspace/libraries/{library_b_id}",
                json={"paper_ids": [paper_b["paper_id"]]},
            )
            assert patch_a.status_code == 200
            assert patch_b.status_code == 200
            assert patch_a.json()["paper_ids"] == [paper_a["paper_id"]]
            assert patch_b.json()["paper_ids"] == [paper_b["paper_id"]]

            reloaded_workspace = client.get("/workspace")
            assert reloaded_workspace.status_code == 200
            libraries_by_id = {
                library["id"]: library for library in reloaded_workspace.json()["libraries"]
            }
            assert libraries_by_id[library_a_id]["paper_ids"] == [paper_a["paper_id"]]
            assert libraries_by_id[library_b_id]["paper_ids"] == [paper_b["paper_id"]]
            assert empty_library.json()["paper_ids"] == []

            scoped_a = client.post(
                "/retrieval/search",
                json={
                    "query": "find scoped evidence for paper A",
                    "paper_ids": libraries_by_id[library_a_id]["paper_ids"],
                    "top_k": 5,
                },
            )
            assert scoped_a.status_code == 200
            scoped_a_body = scoped_a.json()
            assert scoped_a_body["evidence"]
            assert {item["paper_id"] for item in scoped_a_body["evidence"]} == {
                paper_a["paper_id"]
            }
            assert all(item["page_number"] == 1 for item in scoped_a_body["evidence"])
            assert all(
                item["image_url"] == f"/papers/{paper_a['paper_id']}/pages/1/image"
                for item in scoped_a_body["evidence"]
            )
            assert paper_b["paper_id"] not in scoped_a.text

            scoped_b = client.post(
                "/retrieval/search",
                json={
                    "query": "find scoped evidence for paper B",
                    "paper_ids": libraries_by_id[library_b_id]["paper_ids"],
                    "top_k": 5,
                },
            )
            assert scoped_b.status_code == 200
            scoped_b_body = scoped_b.json()
            assert scoped_b_body["evidence"]
            assert {item["paper_id"] for item in scoped_b_body["evidence"]} == {
                paper_b["paper_id"]
            }
            assert paper_a["paper_id"] not in scoped_b.text

            empty_scope = client.post(
                "/retrieval/search",
                json={
                    "query": "empty active library should not search other papers",
                    "paper_ids": empty_library.json()["paper_ids"],
                    "top_k": 5,
                },
            )
            assert empty_scope.status_code == 200
            assert empty_scope.json()["evidence"] == []
            assert empty_scope.json()["note"] == "No paper scope selected; returning no evidence."
            assert paper_a["paper_id"] not in empty_scope.text
            assert paper_b["paper_id"] not in empty_scope.text
    finally:
        asyncio.run(_close_qdrant_client(vector_store))
