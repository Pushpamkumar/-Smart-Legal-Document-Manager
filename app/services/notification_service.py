import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        document_id: int,
        version_id: int,
        similarity: float,
        message: str,
        details: str | None = None,
    ) -> Notification:
        notification = Notification(
            document_id=document_id,
            version_id=version_id,
            similarity_score=similarity,
            message=message,
            details=details,
            triggered=True,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        logger.info(
            "notification_created document_id=%s version_id=%s similarity=%.4f",
            document_id,
            version_id,
            similarity,
        )
        return notification


def enqueue_notification(document_id: int, version_id: int, similarity: float, message: str, details: str | None = None) -> None:
    with SessionLocal() as db:
        service = NotificationService(db)
        service.create_notification(
            document_id=document_id,
            version_id=version_id,
            similarity=similarity,
            message=message,
            details=details,
        )
