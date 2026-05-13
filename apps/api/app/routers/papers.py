from fastapi import APIRouter, Depends, File, Form, Path, UploadFile
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.schemas.papers import PAPER_ID_PATTERN, PaperListResponse, PaperUploadResponse
from app.services.indexing_service import IndexingService
from app.services.ingestion_service import IngestionService
from app.services.pdf_renderer import PdfRenderer
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService

router = APIRouter()


def get_ingestion_service(settings: Settings = Depends(get_settings)) -> IngestionService:
    renderer = PdfRenderer(zoom=settings.pdf_render_zoom, max_pages=settings.max_pdf_pages)
    indexing_service = IndexingService(
        visrag=VisRAGService(settings=settings),
        vector_store=VectorStore(settings=settings),
    )
    return IngestionService(
        paths=StoragePaths(settings),
        renderer=renderer,
        indexing_service=indexing_service,
        max_upload_bytes=settings.max_upload_bytes,
    )


def get_page_image_service(settings: Settings = Depends(get_settings)) -> IngestionService:
    return IngestionService(
        paths=StoragePaths(settings),
        renderer=PdfRenderer(zoom=settings.pdf_render_zoom, max_pages=settings.max_pdf_pages),
        indexing_service=None,
        max_upload_bytes=settings.max_upload_bytes,
    )


@router.post("/upload", response_model=PaperUploadResponse, status_code=201)
async def upload_paper(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    service: IngestionService = Depends(get_ingestion_service),
) -> PaperUploadResponse:
    paper = await service.accept_pdf_upload(file=file, title=title)
    return PaperUploadResponse(paper=paper)


@router.get("", response_model=PaperListResponse)
def list_papers(service: IngestionService = Depends(get_ingestion_service)) -> PaperListResponse:
    return PaperListResponse(papers=service.list_papers())


@router.get("/{paper_id}/status")
def get_paper_status(
    paper_id: str,
    service: IngestionService = Depends(get_ingestion_service),
) -> PaperUploadResponse:
    return PaperUploadResponse(paper=service.get_paper(paper_id))


@router.get("/{paper_id}/pages/{page_number}/image")
def get_paper_page_image(
    paper_id: str = Path(pattern=PAPER_ID_PATTERN),
    page_number: int = Path(ge=1),
    service: IngestionService = Depends(get_page_image_service),
) -> FileResponse:
    image_path = service.get_page_image_path(paper_id=paper_id, page_number=page_number)
    return FileResponse(
        path=image_path,
        media_type="image/png",
        filename=f"{paper_id}-page-{page_number:04d}.png",
    )
