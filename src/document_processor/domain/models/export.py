from uuid import UUID

from pydantic import BaseModel

from document_processor.domain.models.document import DocumentStatus, DocumentType
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult


class DocumentExport(BaseModel):
    """A flattened, export-ready representation of a document's extracted data."""

    document_id: UUID
    type: DocumentType
    region: str
    status: DocumentStatus
    parsed_data: ParsedData | None = None
    validation_result: ValidationResult | None = None
