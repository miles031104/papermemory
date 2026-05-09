from fastapi import APIRouter

from app.core.config import get_settings
from app.core.paths import StoragePaths
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    paths = StoragePaths(settings)
    paths.ensure_all()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        storage_root=str(paths.root),
    )
