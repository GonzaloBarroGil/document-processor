from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from document_processor.core.errors import OCRFailureError
from document_processor.domain.models.audit import AuditAction
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.ports.ocr import OCRResult
from document_processor.domain.services.document_service import DocumentService


def _make_document() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.PENDING,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        created_at=now,
        updated_at=now,
    )


class TestDocumentServiceAudit:
    @pytest.fixture
    def repo(self) -> MagicMock:
        r = MagicMock()
        r.update_status = AsyncMock()
        r.update_parsed_data = AsyncMock()
        return r

    @pytest.fixture
    def storage(self) -> MagicMock:
        s = MagicMock()
        s.retrieve = AsyncMock(return_value=b"image")
        return s

    @pytest.fixture
    def ocr(self) -> MagicMock:
        o = MagicMock()
        o.provider = "paddle"
        o.extract = AsyncMock(return_value=OCRResult("total: 100", 0.95))
        return o

    @pytest.fixture
    def audit(self) -> MagicMock:
        a = MagicMock()
        a.record = AsyncMock()
        return a

    def _service(
        self,
        repo: MagicMock,
        storage: MagicMock,
        ocr: MagicMock,
        audit: MagicMock | None = None,
        failed_extraction: MagicMock | None = None,
    ) -> DocumentService:
        return DocumentService(
            repository=repo,
            storage=storage,
            ocr=ocr,
            validator_registry={},
            audit=audit,
            failed_extraction=failed_extraction,
        )

    async def test_process_records_ocr_and_validate_audit(
        self, repo: MagicMock, storage: MagicMock, ocr: MagicMock, audit: MagicMock
    ) -> None:
        service = self._service(repo, storage, ocr, audit=audit)

        await service.process_document(_make_document())

        assert audit.record.call_count == 2
        actions = [c.kwargs["action"] for c in audit.record.call_args_list]
        assert AuditAction.OCR in actions
        assert AuditAction.VALIDATE in actions

    async def test_process_failure_records_dead_letter(
        self, repo: MagicMock, storage: MagicMock, ocr: MagicMock
    ) -> None:
        failed = MagicMock()
        failed.record_failure = AsyncMock()
        ocr.extract = AsyncMock(side_effect=OCRFailureError("boom"))

        service = self._service(repo, storage, ocr, failed_extraction=failed)

        doc = _make_document()
        await service.process_document(doc)

        failed.record_failure.assert_called_once_with(doc.id, "boom")
        repo.update_status.assert_any_call(doc.id, DocumentStatus.OCR_FAILED)
