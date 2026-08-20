from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from document_processor.adapters.persistence.postgresql.models import Base
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
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.export_service import ExportService
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


def _make_doc(status: DocumentStatus, parsed_data: ParsedData | None = None) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=status,
        media_type=MediaType.JPEG,
        image_key=f"{uuid4()}.jpg",
        parsed_data=parsed_data,
        created_at=now,
        updated_at=now,
    )


class TestReviewFlow:
    async def test_approve_persists_review(self, session_factory) -> None:
        reviewer = _make_reviewer()
        doc = _make_doc(DocumentStatus.VALIDATION_FAILED)

        async with session_factory() as session:
            await PostgresUserRepository(session).create_user(reviewer)
            repo = PostgresDocumentRepository(session)
            await repo.create(doc)

            service = ReviewService(repository=repo)
            updated = await service.review(
                doc.id, reviewer.id, ReviewAction.APPROVE, {"total": "1500.00"}
            )

            assert updated.reviewed is True
            assert updated.reviewed_by == reviewer.id
            assert updated.status == DocumentStatus.COMPLETED
            assert updated.edited_fields == {"total": "1500.00"}


class TestExportFlow:
    async def test_export_json_and_csv(self, session_factory) -> None:
        doc = _make_doc(
            DocumentStatus.COMPLETED,
            parsed_data=ParsedData(
                raw_text="total: 100",
                confidence=0.95,
                fields={"total": "100"},
            ),
        )

        async with session_factory() as session:
            repo = PostgresDocumentRepository(session)
            await repo.create(doc)

            service = ExportService(repository=repo)
            export = await service.export(doc.id)

            assert export.document_id == doc.id
            assert export.parsed_data is not None
            assert export.parsed_data.fields["total"] == "100"

            csv_text = service.to_csv(export)
            assert "total,100" in csv_text
