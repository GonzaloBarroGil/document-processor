from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.export import DocumentExport
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.services.export_service import ExportService


def _make_document() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.COMPLETED,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        parsed_data=ParsedData(
            raw_text="Total: 1500",
            confidence=0.95,
            fields={"total": "1500", "vendor": "Foo"},
        ),
        created_at=now,
        updated_at=now,
    )


class TestExportService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, repo: MagicMock) -> ExportService:
        return ExportService(repository=repo)

    async def test_export_returns_flattened(self, service: ExportService, repo: MagicMock) -> None:
        doc = _make_document()
        repo.get_by_id = AsyncMock(return_value=doc)

        result = await service.export(doc.id)

        assert result.document_id == doc.id
        assert result.type == DocumentType.INVOICE
        assert result.parsed_data is not None
        assert result.parsed_data.fields["total"] == "1500"

    async def test_export_not_found(self, service: ExportService, repo: MagicMock) -> None:
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(DocumentNotFoundError):
            await service.export(uuid4())

    def test_to_csv_flattens_fields(self, service: ExportService) -> None:
        export = DocumentExport(
            document_id=uuid4(),
            type=DocumentType.INVOICE,
            region="AR",
            status=DocumentStatus.COMPLETED,
            parsed_data=ParsedData(
                raw_text="t",
                confidence=0.9,
                fields={"total": "1500", "vendor": "Foo"},
            ),
        )

        csv_text = service.to_csv(export)

        assert "field,value" in csv_text
        assert "total,1500" in csv_text
        assert "vendor,Foo" in csv_text
        assert "status,COMPLETED" in csv_text
