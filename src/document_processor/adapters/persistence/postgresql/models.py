from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.models.validation import (
    ValidationResult,
)


class Base(DeclarativeBase):
    """Declarative base class for SQLAlchemy ORM models."""

    pass


class DocumentModel(Base):
    """SQLAlchemy ORM model for persisted documents."""

    __tablename__ = "documents"
    __table_args__ = (Index("idx_documents_user", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_fields: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)


class ApiKeyModel(Base):
    """SQLAlchemy ORM model for persisted API keys."""

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StorageAlertModel(Base):
    """SQLAlchemy ORM model for storage usage alerts."""

    __tablename__ = "storage_alerts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class UserModel(Base):
    """SQLAlchemy ORM model for human users."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="REVIEWER")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class RefreshTokenModel(Base):
    """SQLAlchemy ORM model for rotating refresh tokens."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ExtractionAuditModel(Base):
    """SQLAlchemy ORM model for the immutable extraction audit trail."""

    __tablename__ = "extraction_audit"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class FailedExtractionModel(Base):
    """SQLAlchemy ORM model for the failed-extraction dead-letter queue."""

    __tablename__ = "failed_extractions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class DailyUsageModel(Base):
    """SQLAlchemy ORM model for the daily ingestion usage counters."""

    __tablename__ = "daily_usage"

    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


def document_to_model(doc: Document) -> DocumentModel:
    """Convert a domain Document to its persistence model."""
    return DocumentModel(
        id=doc.id,
        type=doc.type.value,
        region=doc.region,
        status=doc.status.value,
        media_type=doc.media_type.value,
        image_key=doc.image_key,
        user_id=doc.user_id,
        parsed_data=doc.parsed_data.model_dump() if doc.parsed_data else None,
        validation_result=doc.validation_result.model_dump() if doc.validation_result else None,
        error_detail=doc.error_detail,
        reviewed=doc.reviewed,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        edited_fields=doc.edited_fields,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def model_to_document(model: DocumentModel) -> Document:
    """Convert a persistence model to a domain Document."""
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
        user_id=model.user_id,
        parsed_data=parsed_data,
        validation_result=validation_result,
        error_detail=model.error_detail,
        reviewed=model.reviewed,
        reviewed_by=model.reviewed_by,
        reviewed_at=model.reviewed_at,
        edited_fields=model.edited_fields,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def user_to_model(user: User) -> UserModel:
    """Convert a domain User to its persistence model."""
    return UserModel(
        id=user.id,
        username=user.username,
        password_hash=user.password_hash,
        role=user.role.value,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def model_to_user(model: UserModel) -> User:
    """Convert a persistence model to a domain User."""
    return User(
        id=model.id,
        username=model.username,
        password_hash=model.password_hash,
        role=UserRole(model.role),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
