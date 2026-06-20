from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult


class DocumentType(StrEnum):
    INVOICE = "invoice"
    TICKET = "ticket"
    PAYMENT_RECEIPT = "payment_receipt"


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    OCR_IN_PROGRESS = "OCR_IN_PROGRESS"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    OCR_FAILED = "OCR_FAILED"
    IMAGE_EXPIRED = "IMAGE_EXPIRED"


class MediaType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    HEIC = "image/heic"
    PDF = "application/pdf"


class Document(BaseModel):
    id: UUID
    type: DocumentType
    region: str
    status: DocumentStatus
    media_type: MediaType
    image_key: str
    parsed_data: ParsedData | None = None
    validation_result: ValidationResult | None = None
    error_detail: str | None = None
    created_at: datetime
    updated_at: datetime
