from pathlib import Path

from app.core.config import Settings


def test_default_cors_origins_allow_localhost_and_loopback(monkeypatch) -> None:
    monkeypatch.delenv("PAPERMEMORY_CORS_ORIGINS", raising=False)

    settings = Settings(_env_file=None)

    assert "http://localhost:3000" in settings.cors_origins
    assert "http://127.0.0.1:3000" in settings.cors_origins


def test_cors_origins_env_override_is_preserved(monkeypatch) -> None:
    monkeypatch.setenv(
        "PAPERMEMORY_CORS_ORIGINS",
        '["http://example.test:3000"]',
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://example.test:3000"]


def test_qdrant_local_path_relative_to_storage_root(tmp_path) -> None:
    storage_root = tmp_path / "storage"
    settings = Settings(
        storage_root=storage_root,
        qdrant_mode="local",
        qdrant_local_path=Path("qdrant-local"),
    )

    assert settings.storage_root == storage_root
    assert settings.qdrant_local_path == storage_root / "qdrant-local"


def test_qdrant_local_path_absolute_is_preserved(tmp_path) -> None:
    local_path = tmp_path / "absolute-qdrant"
    settings = Settings(qdrant_mode="local", qdrant_local_path=local_path)

    assert settings.qdrant_local_path == local_path


def test_qdrant_local_path_storage_prefix_is_relative_to_repo_root() -> None:
    settings = Settings(qdrant_mode="local")

    assert settings.qdrant_local_path == settings.storage_root / "qdrant_local"
