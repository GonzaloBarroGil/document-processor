from uuid import UUID

from document_processor.domain.models.document import DocumentStatus
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)


class PersistOutput:
    def __init__(self, success: bool) -> None:
        self.success = success


async def persist(
    repository: DocumentRepositoryPort,
    document_id: UUID,
    parsed_data: ParsedData,
    validation_result: ValidationResult | None,
    status: DocumentStatus,
) -> PersistOutput:
    await repository.update_parsed_data(
        document_id=document_id,
        parsed_data=parsed_data,
        validation_result=validation_result,
    )
    await repository.update_status(document_id=document_id, status=status)
    return PersistOutput(success=True)
