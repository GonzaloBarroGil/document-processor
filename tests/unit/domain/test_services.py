from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from document_processor.core.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedMediaTypeError,
)
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.storage_lifecycle import (
    StorageLifecycleService,
)


def _make_document(
    status: DocumentStatus = DocumentStatus.PENDING,
    doc_id: UUID | None = None,
    region: str = "AR",
    media_type: MediaType = MediaType.JPEG,
) -> Document:
    return Document(
        id=doc_id or uuid4(),
        type=DocumentType.INVOICE,
        region=region,
        status=status,
        media_type=media_type,
        image_key=f"{doc_id}.jpg" if doc_id else "key.jpg",
        parsed_data=None,
        validation_result=None,
        error_detail=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestDocumentService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def storage(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def ocr(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        repo: MagicMock,
        storage: MagicMock,
        ocr: MagicMock,
    ) -> DocumentService:
        return DocumentService(
            repository=repo,
            storage=storage,
            ocr=ocr,
            validator_registry={},
        )

    async def test_ingest_document_success(
        self, service: DocumentService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.create = AsyncMock()
        storage.store = AsyncMock()

        doc = await service.ingest_document(
            file_bytes=b"fake-jpeg-data",
            filename="invoice.jpg",
            document_type_value="invoice",
            region="AR",
            media_type_value="image/jpeg",
        )

        assert doc.status == DocumentStatus.PENDING
        assert doc.type == DocumentType.INVOICE
        assert doc.region == "AR"
        repo.create.assert_called_once()
        storage.store.assert_called_once()

    async def test_ingest_document_unsupported_type(
        self, service: DocumentService
    ) -> None:
        with pytest.raises(UnsupportedMediaTypeError):
            await service.ingest_document(
                file_bytes=b"data",
                filename="file.tar",
                document_type_value="invoice",
                region="AR",
                media_type_value="application/x-tar",
            )

    async def test_ingest_document_file_too_large(
        self, service: DocumentService
    ) -> None:
        with pytest.raises(FileTooLargeError):
            await service.ingest_document(
                file_bytes=b"x" * (11 * 1024 * 1024),
                filename="big.jpg",
                document_type_value="invoice",
                region="AR",
                media_type_value="image/jpeg",
            )

    async def test_get_document_found(
        self, service: DocumentService, repo: MagicMock
    ) -> None:
        doc = _make_document()
        repo.get_by_id = AsyncMock(return_value=doc)

        result = await service.get_document(doc.id)
        assert result.id == doc.id

    async def test_get_document_not_found(
        self, service: DocumentService, repo: MagicMock
    ) -> None:
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(DocumentNotFoundError):
            await service.get_document(
                UUID("00000000-0000-0000-0000-000000000001")
            )

    async def test_list_documents(
        self, service: DocumentService, repo: MagicMock
    ) -> None:
        repo.list_documents = AsyncMock(return_value=([], 0))

        docs, total = await service.list_documents(page=1, size=10)
        assert docs == []
        assert total == 0


class TestStorageLifecycleService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def storage(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self, repo: MagicMock, storage: MagicMock
    ) -> StorageLifecycleService:
        return StorageLifecycleService(repository=repo, storage=storage)

    async def test_usage_below_watermark_no_expiry(
        self, service: StorageLifecycleService, storage: MagicMock
    ) -> None:
        storage.usage_pct = AsyncMock(return_value=50.0)

        expired = await service.evaluate()
        assert expired == []

    async def test_usage_above_high_watermark_expires_completed(
        self,
        service: StorageLifecycleService,
        storage: MagicMock,
        repo: MagicMock,
    ) -> None:
        storage.usage_pct = AsyncMock(return_value=90.0)
        old_doc = _make_document(
            status=DocumentStatus.COMPLETED,
            doc_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        old_doc.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        repo.list_documents = AsyncMock(return_value=([old_doc], 1))
        repo.update_status = AsyncMock()
        storage.delete = AsyncMock()

        expired = await service.evaluate()
        assert len(expired) == 1
        storage.delete.assert_called_once()
