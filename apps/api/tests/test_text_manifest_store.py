import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.services.page_text_extractor import (
    PageTextEntry,
    PageTextQuality,
    TextBlock,
    TextManifest,
    TextWord,
)
from app.services.text_manifest_store import TextManifestStore


def _manifest(paper_id: str = "paper-1") -> TextManifest:
    return TextManifest(
        paper_id=paper_id,
        page_count=1,
        pages=[
            PageTextEntry(
                paper_id=paper_id,
                page_number=1,
                width=320.0,
                height=240.0,
                text="Deterministic manifest text.",
                caption="Deterministic manifest text.",
                blocks=[
                    TextBlock(
                        block_number=0,
                        text="Deterministic manifest text.",
                        bbox=(1.0, 2.0, 3.0, 4.0),
                        word_count=3,
                    )
                ],
                words=[
                    TextWord(
                        text="Deterministic",
                        bbox=(1.0, 2.0, 3.0, 4.0),
                        block_number=0,
                        line_number=0,
                        word_number=0,
                    )
                ],
                quality=PageTextQuality(
                    char_count=28,
                    word_count=3,
                    block_count=1,
                    has_text=True,
                    ocr_needed=False,
                    quality_label="good",
                ),
            )
        ],
    )


def test_save_reload_is_deterministic_under_text_manifest_index(tmp_path: Path) -> None:
    paths = StoragePaths(Settings(storage_root=tmp_path))
    store = TextManifestStore(paths)
    manifest = _manifest()

    manifest_path = store.save(manifest)
    first_bytes = manifest_path.read_bytes()
    loaded = store.load("paper-1")
    second_path = store.save(loaded)
    second_bytes = second_path.read_bytes()

    assert manifest_path == tmp_path / "indexes" / "text_manifests" / "paper-1.json"
    assert manifest_path.is_file()
    assert loaded == manifest
    assert second_bytes == first_bytes

    payload = json.loads(first_bytes.decode("utf-8"))
    assert payload["schema_version"] == "text_manifest.v0"
    assert payload["paper_id"] == "paper-1"
    assert payload["pages"][0]["quality"]["quality_label"] == "good"


def test_rejects_unsafe_paper_ids(tmp_path: Path) -> None:
    store = TextManifestStore(StoragePaths(Settings(storage_root=tmp_path)))

    for paper_id in ["", "../escape", "nested/paper", ".hidden", "paper id"]:
        with pytest.raises(ValueError):
            store.path_for(paper_id)
        with pytest.raises(ValueError):
            store.load(paper_id)
        with pytest.raises(ValueError):
            store.save(_manifest(paper_id=paper_id))


def test_path_for_stays_inside_storage_index_root(tmp_path: Path) -> None:
    store = TextManifestStore(StoragePaths(Settings(storage_root=tmp_path)))

    path = store.path_for("Paper_1-abc")

    assert path == tmp_path / "indexes" / "text_manifests" / "Paper_1-abc.json"
    path.resolve().relative_to((tmp_path / "indexes" / "text_manifests").resolve())
