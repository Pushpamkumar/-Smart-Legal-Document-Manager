from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.schemas.document_schema import (
    DeleteResponse,
    DiffResponse,
    DocumentContentUpdate,
    DocumentContentUpdateResponse,
    DocumentCreate,
    DocumentCreateResponse,
    DocumentResponse,
    DocumentTitleUpdate,
    PaginatedVersionsResponse,
)
from app.services.document_service import DocumentService
from app.services.notification_service import enqueue_notification

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


@router.post("", response_model=DocumentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, service: DocumentService = Depends(get_document_service)) -> DocumentCreateResponse:
    document, version = service.create_document(payload)
    return DocumentCreateResponse(document=document, latest_version=version)


@router.put("/{document_id}/content", response_model=DocumentContentUpdateResponse)
def update_document_content(
    document_id: int,
    payload: DocumentContentUpdate,
    background_tasks: BackgroundTasks,
    service: DocumentService = Depends(get_document_service),
) -> DocumentContentUpdateResponse:
    version, created, message, similarity = service.update_content(document_id, payload)

    if created and similarity is not None and similarity < settings.similarity_threshold:
        background_tasks.add_task(
            enqueue_notification,
            document_id,
            version.version_id,
            similarity,
            f"Significant update detected for document {document_id} version v{version.version_number}.",
            f"Similarity score {similarity:.4f} is below threshold {settings.similarity_threshold:.2f}.",
        )

    return DocumentContentUpdateResponse(
        document_id=document_id,
        version_created=created,
        message=message,
        latest_version=version,
        similarity_score=similarity,
    )


@router.put("/{document_id}/title", response_model=DocumentResponse)
def update_document_title(
    document_id: int,
    payload: DocumentTitleUpdate,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    return service.update_title(document_id, payload.title)


@router.get("/{document_id}/versions", response_model=PaginatedVersionsResponse)
def list_document_versions(
    document_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.page_size_default, ge=1, le=settings.page_size_max),
    service: DocumentService = Depends(get_document_service),
) -> PaginatedVersionsResponse:
    return service.list_versions(document_id, page, page_size)


@router.get("/{document_id}/compare", response_model=DiffResponse)
def compare_document_versions(
    document_id: int,
    v1: int = Query(..., ge=1),
    v2: int = Query(..., ge=1),
    service: DocumentService = Depends(get_document_service),
) -> DiffResponse:
    return service.compare_versions(document_id, v1, v2)


@router.delete("/{document_id}", response_model=DeleteResponse)
def delete_document(document_id: int, service: DocumentService = Depends(get_document_service)) -> DeleteResponse:
    service.delete_document(document_id)
    return DeleteResponse(message="Document deleted successfully.")


@router.delete("/{document_id}/versions/{version_number}", response_model=DeleteResponse)
def delete_version(
    document_id: int,
    version_number: int,
    service: DocumentService = Depends(get_document_service),
) -> DeleteResponse:
    service.delete_version(document_id, version_number)
    return DeleteResponse(message="Document version deleted successfully.")
