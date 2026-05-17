from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "PaperMemory API"
    app_version: str = "0.1.0"
    environment: str = "local"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    storage_root: Path = REPO_ROOT / "storage"
    max_upload_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    max_pdf_pages: int = Field(default=200, gt=0)
    pdf_render_zoom: float = Field(default=2.0, gt=0)

    qdrant_mode: Literal["server", "local"] = "server"
    qdrant_url: str = "http://localhost:6333"
    qdrant_local_path: Path = Path("storage") / "qdrant_local"
    qdrant_collection: str = "papermemory_pages"
    qdrant_vector_size: int = Field(
        default=8,
        ge=1,
        description="Use 8 for stub retrieval and 2304 for real VisRAG-Ret embeddings.",
    )
    qdrant_distance: Literal["Cosine", "Dot", "Euclid", "Manhattan"] = "Cosine"
    qdrant_timeout_seconds: float = Field(default=5.0, gt=0)

    visrag_backend: Literal["stub", "transformers"] = "stub"
    visrag_model_name: str = "openbmb/VisRAG-Ret"
    visrag_instruction: str = (
        "Represent this query for retrieving relevant documents:"
    )
    visrag_device: Literal["auto", "cpu", "cuda"] = "auto"
    visrag_dtype: Literal["auto", "float32", "float16", "bfloat16"] = "auto"
    visrag_trust_remote_code: bool = False
    visrag_batch_size: int = Field(default=4, ge=1)

    byok_base_url: AnyHttpUrl | None = None
    byok_api_key: str | None = None
    byok_model: str = "gpt-4.1-mini"
    byok_timeout_seconds: float = Field(default=60.0, gt=0)
    byok_enable_image_context: bool = False
    byok_max_evidence_images: int = Field(default=3, ge=0, le=10)
    byok_max_image_bytes: int = Field(default=2 * 1024 * 1024, gt=0)

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_prefix="PAPERMEMORY_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def resolve_local_paths(self) -> "Settings":
        if not self.storage_root.is_absolute():
            self.storage_root = REPO_ROOT / self.storage_root
        if not self.qdrant_local_path.is_absolute():
            first_part = self.qdrant_local_path.parts[0].lower() if self.qdrant_local_path.parts else ""
            if first_part == "storage":
                self.qdrant_local_path = REPO_ROOT / self.qdrant_local_path
            else:
                self.qdrant_local_path = self.storage_root / self.qdrant_local_path
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
