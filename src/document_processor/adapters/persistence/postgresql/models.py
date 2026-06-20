from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import (
    ValidationError,
    ValidationResult,
)


class Base(DeclarativeBase):
    pass


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StorageAlertModel(Base):
    __tablename__ = "storage_alerts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


def document_to_model(doc: Document) -> DocumentModel:
    return DocumentModel(
        id=doc.id,
        type=doc.type.value,
        region=doc.region,
        status=doc.status.value,
        media_type=doc.media_type.value,
        image_key=doc.image_key,
        parsed_data=doc.parsed_data.model_dump() if doc.parsed_data else None,
        validation_result=doc.validation_result.model_dump() if doc.validation_result else None,
        error_detail=doc.error_detail,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def model_to_document(model: DocumentModel) -> Document:
    parsed_data = None
    if model.parsed_data:
        parsed_data = ParsedData(**model.parsed_data)

    validation_result = None
    if model.validation_result:
        validation_result = ValidationResult(**model.validation_result)

    return Document(
        id=model.id,
        type=DocumentType(model.type),
        region=model.region,
        status=DocumentStatus(model.status),
        media_type=MediaType(model.media_type),
        image_key=model.image_key,
        parsed_data=parsed_data,
        validation_result=validation_result,
        error_detail=model.error_detail,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
