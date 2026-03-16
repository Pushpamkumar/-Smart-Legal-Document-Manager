from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_document_version", "document_id", "version_id"),
        Index("ix_notifications_created_at", "created_at"),
    )

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.document_id"), nullable=False)
    version_id: Mapped[int] = mapped_column(ForeignKey("document_versions.version_id"), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    triggered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("Document")
    version = relationship("DocumentVersion")
