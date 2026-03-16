import logging
import math

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.version import DocumentVersion
from app.schemas.document_schema import DocumentContentUpdate, DocumentCreate, PaginatedVersionsResponse
from app.services.user_service import UserService
from app.utils.content import normalize_content
from app.utils.diff_engine import build_diff
from app.utils.similarity import similarity_score

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)

    def create_document(self, payload: DocumentCreate) -> tuple[Document, DocumentVersion]:
        with self.db.begin():
            user = self.user_service.get_or_create_user(payload.author_name, payload.author_email)
            document = Document(title=payload.title, created_by=user.user_id)
            self.db.add(document)
            self.db.flush()

            version = DocumentVersion(
                document_id=document.document_id,
                version_number=1,
                content=payload.content,
                created_by=user.user_id,
            )
            self.db.add(version)
            self.db.flush()

        self.db.refresh(document)
        self.db.refresh(version)
        logger.info("document_created document_id=%s version_id=%s", document.document_id, version.version_id)
        return document, version

    def _document_query(self) -> Select[tuple[Document]]:
        return select(Document).where(Document.is_deleted.is_(False))

    def get_document(self, document_id: int) -> Document:
        document = self.db.scalar(self._document_query().where(Document.document_id == document_id))
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return document

    def get_version(self, document_id: int, version_number: int) -> DocumentVersion:
        version = self.db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == version_number,
                DocumentVersion.is_deleted.is_(False),
            )
        )
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        return version

    def get_latest_version(self, document_id: int) -> DocumentVersion | None:
        return self.db.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id, DocumentVersion.is_deleted.is_(False))
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )

    def update_title(self, document_id: int, title: str) -> Document:
        document = self.get_document(document_id)
        try:
            document.title = title
            self.db.add(document)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(document)
        logger.info("document_title_updated document_id=%s", document_id)
        return document

    def update_content(self, document_id: int, payload: DocumentContentUpdate) -> tuple[DocumentVersion, bool, str, float | None]:
        document = self.get_document(document_id)
        user = self.user_service.get_user_by_email(payload.created_by_email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

        latest_version = self.get_latest_version(document_id)
        if not latest_version:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document has no active versions")

        if payload.base_version_number and payload.base_version_number != latest_version.version_number:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Version conflict. Latest version is v{latest_version.version_number}",
            )

        if normalize_content(latest_version.content) == normalize_content(payload.content):
            return latest_version, False, "No new version created because the content is effectively identical.", None

        similarity = similarity_score(latest_version.content, payload.content)

        try:
            max_version_number = self.db.scalar(
                select(func.max(DocumentVersion.version_number)).where(DocumentVersion.document_id == document_id)
            )
            next_version_number = (max_version_number or 0) + 1

            new_version = DocumentVersion(
                document_id=document.document_id,
                version_number=next_version_number,
                content=payload.content,
                created_by=user.user_id,
            )
            self.db.add(new_version)
            document.updated_at = func.now()
            self.db.add(document)
            self.db.flush()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(new_version)
        logger.info(
            "document_version_created document_id=%s version_number=%s similarity=%.4f",
            document_id,
            new_version.version_number,
            similarity,
        )
        return new_version, True, "New document version created successfully.", similarity

    def list_versions(self, document_id: int, page: int, page_size: int) -> PaginatedVersionsResponse:
        self.get_document(document_id)
        page_size = min(page_size, settings.page_size_max)

        total_items = self.db.scalar(
            select(func.count(DocumentVersion.version_id)).where(
                DocumentVersion.document_id == document_id, DocumentVersion.is_deleted.is_(False)
            )
        ) or 0

        items = list(
            self.db.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id, DocumentVersion.is_deleted.is_(False))
                .order_by(DocumentVersion.version_number.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )

        total_pages = math.ceil(total_items / page_size) if total_items else 0
        return PaginatedVersionsResponse(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    def compare_versions(self, document_id: int, v1: int, v2: int):
        version_1 = self.get_version(document_id, v1)
        version_2 = self.get_version(document_id, v2)
        return build_diff(document_id, v1, version_1.content, v2, version_2.content)

    def delete_document(self, document_id: int) -> None:
        document = self.get_document(document_id)
        try:
            document.is_deleted = True
            self.db.add(document)
            versions = self.db.scalars(
                select(DocumentVersion).where(DocumentVersion.document_id == document_id, DocumentVersion.is_deleted.is_(False))
            )
            for version in versions:
                version.is_deleted = True
                self.db.add(version)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        logger.info("document_deleted document_id=%s", document_id)

    def delete_version(self, document_id: int, version_number: int) -> None:
        self.get_document(document_id)
        version = self.get_version(document_id, version_number)
        try:
            version.is_deleted = True
            self.db.add(version)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        logger.info("document_version_deleted document_id=%s version_number=%s", document_id, version_number)
