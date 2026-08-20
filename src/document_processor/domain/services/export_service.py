import csv
import io
from uuid import UUID

from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.export import DocumentExport
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)


class ExportService:
    """Builds export-ready representations of a document's extracted data."""

    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    async def export(self, document_id: UUID) -> DocumentExport:
        """Return a flattened export payload for the given document."""
        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(str(document_id))

        return DocumentExport(
            document_id=document.id,
            type=document.type,
            region=document.region,
            status=document.status,
            parsed_data=document.parsed_data,
            validation_result=document.validation_result,
        )

    @staticmethod
    def to_csv(export: DocumentExport) -> str:
        """Render the export payload as a flattened key-value CSV."""
        fields = export.parsed_data.fields if export.parsed_data else {}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["field", "value"])
        writer.writerow(["document_id", str(export.document_id)])
        writer.writerow(["type", export.type.value])
        writer.writerow(["region", export.region])
        writer.writerow(["status", export.status.value])
        for key in sorted(fields):
            writer.writerow([key, fields[key]])
        return output.getvalue()
