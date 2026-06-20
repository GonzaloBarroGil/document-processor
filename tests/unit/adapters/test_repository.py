from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from document_processor.adapters.persistence.postgresql.models import (
    document_to_model,
    model_to_document,
)
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult


def _make_domain_doc(
    doc_id: UUID | None = None,
    status: DocumentStatus = DocumentStatus.PENDING,
) -> Document:
    return Document(
        id=doc_id or uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=status,
        media_type=MediaType.JPEG,
        image_key=f"{doc_id}.jpg" if doc_id else "key.jpg",
        parsed_data=None,
        validation_result=None,
        error_detail=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestDocumentConversion:
    def test_document_to_model_roundtrip(self) -> None:
        doc = _make_domain_doc()
        model = document_to_model(doc)
        result = model_to_document(model)

        assert result.id == doc.id
        assert result.type == doc.type
        assert result.region == doc.region
        assert result.status == doc.status


class TestPostgresDocumentRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.execute = AsyncMock()
        s.add = MagicMock()
        s.flush = AsyncMock()
        s.refresh = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresDocumentRepository:
        return PostgresDocumentRepository(session)

    async def test_create(self, repo: PostgresDocumentRepository, session: MagicMock) -> None:
        doc = _make_domain_doc()

        result = await repo.create(doc)

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.id == doc.id

    async def test_get_by_id_found(
        self, repo: PostgresDocumentRepository, session: MagicMock
    ) -> None:
        doc = _make_domain_doc()
        model = document_to_model(doc)
        session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=model)
            )
        )

        result = await repo.get_by_id(doc.id)

        assert result is not None
        assert result.id == doc.id

    async def test_get_by_id_not_found(
        self, repo: PostgresDocumentRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None)
            )
        )

        result = await repo.get_by_id(UUID("00000000-0000-0000-0000-000000000001"))
        assert result is None

    async def test_update_status(
        self, repo: PostgresDocumentRepository, session: MagicMock
    ) -> None:
        doc_id = uuid4()
        session.execute = AsyncMock()

        await repo.update_status(doc_id, DocumentStatus.COMPLETED)

        session.execute.assert_called_once()

    async def test_update_parsed_data(
        self, repo: PostgresDocumentRepository, session: MagicMock
    ) -> None:
        doc_id = uuid4()
        parsed = ParsedData(raw_text="test", confidence=0.9, fields={})
        validation = ValidationResult(
            passed=True, errors=[], region="AR",
            validated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock()

        await repo.update_parsed_data(doc_id, parsed, validation)

        session.execute.assert_called_once()
