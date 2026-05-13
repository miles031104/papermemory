from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.paths import StoragePaths
from app.schemas.retrieval import PageEvidence
from app.services.page_image_resolver import PageImageResolver


def _resolver(storage_root: Path) -> PageImageResolver:
    return PageImageResolver(StoragePaths(Settings(storage_root=storage_root)))


def test_resolver_rejects_invalid_paper_id(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path)

    resolved = resolver.resolve_evidence_image_path(
        PageEvidence(
            paper_id="../outside",
            page_number=1,
            score=0.9,
            image_path=str(tmp_path / "outside.png"),
        )
    )

    assert resolved is None


def test_resolver_rejects_non_positive_page_number(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path)

    resolved = resolver.resolve_evidence_image_path(
        PageEvidence(
            paper_id="paper-1",
            page_number=0,
            score=0.9,
            image_path=str(tmp_path / "outside.png"),
        )
    )

    assert resolved is None


def test_resolver_skips_missing_controlled_file(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path)

    resolved = resolver.resolve_evidence_image_path(
        PageEvidence(
            paper_id="paper-1",
            page_number=1,
            score=0.9,
            image_path=str(tmp_path / "outside.png"),
        )
    )

    assert resolved is None


def test_resolver_returns_controlled_rendered_page_file(tmp_path: Path) -> None:
    image_path = tmp_path / "rendered_pages" / "paper-1" / "page-0001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nsafe")
    resolver = _resolver(tmp_path)

    resolved = resolver.resolve_evidence_image_path(
        PageEvidence(
            paper_id="paper-1",
            page_number=1,
            score=0.9,
            image_path=str(tmp_path / "outside.png"),
        )
    )

    assert resolved == str(image_path.resolve())


def test_resolver_rejects_symlink_escape(tmp_path: Path) -> None:
    outside_image = tmp_path / "outside.png"
    outside_image.write_bytes(b"\x89PNG\r\n\x1a\nsecret")
    controlled_path = tmp_path / "rendered_pages" / "paper-1" / "page-0001.png"
    controlled_path.parent.mkdir(parents=True)
    try:
        controlled_path.symlink_to(outside_image)
    except OSError as exc:
        pytest.skip(f"Symlink creation is not available in this Windows environment: {exc}")

    resolver = _resolver(tmp_path)

    resolved = resolver.resolve_evidence_image_path(
        PageEvidence(
            paper_id="paper-1",
            page_number=1,
            score=0.9,
            image_path=str(outside_image),
        )
    )

    assert resolved is None
