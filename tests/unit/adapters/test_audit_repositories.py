from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from document_processor.adapters.persistence.postgresql.audit_repository import (
    PostgresAuditRepository,
)
from document_processor.adapters.persistence.postgresql.failed_extraction_repository import (
    PostgresFailedExtractionRepository,
)
from document_processor.adapters.persistence.postgresql.models import (
    FailedExtractionModel,
)
from document_processor.domain.models.audit import AuditAction


class TestPostgresAuditRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.add = MagicMock()
        s.flush = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresAuditRepository:
        return PostgresAuditRepository(session)

    async def test_record(self, repo: PostgresAuditRepository, session: MagicMock) -> None:
        await repo.record(uuid4(), None, "paddle", 0.9, AuditAction.OCR)

        session.add.assert_called_once()
        session.flush.assert_called_once()


class TestPostgresFailedExtractionRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.execute = AsyncMock()
        s.add = MagicMock()
        s.flush = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresFailedExtractionRepository:
        return PostgresFailedExtractionRepository(session)

    async def test_record_new_failure(
        self, repo: PostgresFailedExtractionRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        await repo.record_failure(uuid4(), "boom")

        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_record_existing_increments_retry(
        self, repo: PostgresFailedExtractionRepository, session: MagicMock
    ) -> None:
        model = FailedExtractionModel(
            id=uuid4(),
            document_id=uuid4(),
            retry_count=2,
            last_error="old",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=model))
        )

        await repo.record_failure(model.document_id, "boom")

        assert model.retry_count == 3
        assert model.last_error == "boom"
