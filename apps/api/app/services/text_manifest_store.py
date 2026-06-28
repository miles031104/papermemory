import json
from pathlib import Path

from app.core.paths import StoragePaths
from app.schemas.papers import is_safe_paper_id
from app.services.page_text_extractor import TextManifest


class TextManifestStore:
    """Persists page-text manifests under the local index storage root."""

    def __init__(self, paths: StoragePaths) -> None:
        self.paths = paths
        self.manifest_dir = self.paths.indexes_dir / "text_manifests"

    def path_for(self, paper_id: str) -> Path:
        self._validate_paper_id(paper_id)
        path = self.manifest_dir / f"{paper_id}.json"
        manifest_root = self.manifest_dir.resolve()
        try:
            path.resolve().relative_to(manifest_root)
        except ValueError as exc:
            raise ValueError("Invalid paper id.") from exc
        return path

    def save(self, manifest: TextManifest) -> Path:
        path = self.path_for(manifest.paper_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = manifest.model_dump(mode="json")
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def load(self, paper_id: str) -> TextManifest:
        path = self.path_for(paper_id)
        return TextManifest.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _validate_paper_id(paper_id: str) -> None:
        if not is_safe_paper_id(paper_id):
            raise ValueError("Invalid paper id.")
