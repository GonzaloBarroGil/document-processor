from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from document_processor.adapters.persistence.postgresql.audit_repository import (
    PostgresAuditRepository,
)
from document_processor.adapters.persistence.postgresql.failed_extraction_repository import (
    PostgresFailedExtractionRepository,
)
from document_processor.adapters.persistence.postgresql.models import (
    Base,
    ExtractionAuditModel,
)
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.adapters.persistence.postgresql.user_repository import (
    PostgresUserRepository,
)
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
    ReviewAction,
)
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.ports.ocr import OCRResult
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.review_service import ReviewService


@pytest.fixture(scope="module")
def db_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture
async def session_factory(db_container):
    url = urlparse(db_container.get_connection_url())
    db_url = urlunparse(
        ("postgresql+asyncpg", url.netloc, url.path, url.params, url.query, url.fragment)
    )
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine)
    yield factory

    await engine.dispose()


def _make_reviewer() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="reviewer1",
        password_hash="hash",
        role=UserRole.REVIEWER,
        created_at=now,
        updated_at=now,
    )


def _make_doc() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.PENDING,
        media_type=MediaType.JPEG,
        image_key=f"{uuid4()}.jpg",
        created_at=now,
        updated_at=now,
    )


def _mock_ocr() -> MagicMock:
    ocr = MagicMock()
    ocr.provider = "paddle"
    ocr.extract = AsyncMock(return_value=OCRResult("total: 100", 0.95))
    return ocr


def _mock_storage() -> MagicMock:
    storage = MagicMock()
    storage.retrieve = AsyncMock(return_value=b"fake-image")
    return storage


class TestPipelineEndToEnd:
    async def test_ingest_process_audit_review(self, session_factory) -> None:
        reviewer = _make_reviewer()
        doc = _make_doc()

        async with session_factory() as session:
            repo = PostgresDocumentRepository(session)
            audit = PostgresAuditRepository(session)
            failed = PostgresFailedExtractionRepository(session)
            await PostgresUserRepository(session).create_user(reviewer)

            service = DocumentService(
                repository=repo,
                storage=_mock_storage(),
                ocr=_mock_ocr(),
                validator_registry={},
                audit=audit,
                failed_extraction=failed,
            )

            await repo.create(doc)
            await service.process_document(doc)

            audit_rows = (await session.execute(select(ExtractionAuditModel))).scalars().all()
            assert sorted(r.action for r in audit_rows) == ["OCR", "VALIDATE"]

            review = ReviewService(repository=repo, audit=audit)
            updated = await review.review(doc.id, reviewer.id, ReviewAction.APPROVE)

            assert updated.reviewed is True
            assert updated.status == DocumentStatus.COMPLETED

            audit_rows = (await session.execute(select(ExtractionAuditModel))).scalars().all()
            assert "REVIEW_APPROVE" in [r.action for r in audit_rows]
