from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


def validate_non_blank(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("Value must not be blank")
    return value.strip()


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)

    _validate_name = field_validator("name")(validate_non_blank)
    _validate_email = field_validator("email")(validate_non_blank)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=settings.max_content_length)
    author_name: str = Field(..., min_length=1, max_length=255)
    author_email: str = Field(..., min_length=3, max_length=255)

    _validate_title = field_validator("title")(validate_non_blank)
    _validate_author_name = field_validator("author_name")(validate_non_blank)
    _validate_author_email = field_validator("author_email")(validate_non_blank)


class DocumentTitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

    _validate_title = field_validator("title")(validate_non_blank)


class DocumentContentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=settings.max_content_length)
    created_by_email: str = Field(..., min_length=3, max_length=255)
    base_version_number: int | None = Field(default=None, ge=1)

    _validate_created_by_email = field_validator("created_by_email")(validate_non_blank)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    created_by: int
    is_deleted: bool


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: int
    document_id: int
    version_number: int
    content: str
    created_by: int
    created_at: datetime
    is_deleted: bool


class DocumentCreateResponse(BaseModel):
    document: DocumentResponse
    latest_version: DocumentVersionResponse


class DocumentContentUpdateResponse(BaseModel):
    document_id: int
    version_created: bool
    message: str
    latest_version: DocumentVersionResponse
    similarity_score: float | None = None


class PaginatedVersionsResponse(BaseModel):
    items: list[DocumentVersionResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class DiffEntry(BaseModel):
    before: str | None = None
    after: str | None = None


class DiffResponse(BaseModel):
    document_id: int
    version_1: int
    version_2: int
    added: list[str]
    removed: list[str]
    modified: list[DiffEntry]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    document_id: int
    version_id: int
    message: str
    similarity_score: float
    triggered: bool
    created_at: datetime
    details: str | None = None


class DeleteResponse(BaseModel):
    message: str
