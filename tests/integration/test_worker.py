import uuid
from datetime import UTC, datetime

import pytest
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer

from document_processor.adapters.persistence.postgresql.models import Base
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.adapters.storage.minio import MinioStorage
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData


@pytest.fixture(scope="module")
def db_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="module")
def minio_container():
    with MinioContainer("minio/minio:latest") as minio:
        yield minio


@pytest.fixture
async def db_session(db_container):
    from urllib.parse import urlparse, urlunparse

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    url = urlparse(db_container.get_connection_url())
    db_url = urlunparse(
        ("postgresql+asyncpg", url.netloc, url.path, url.params, url.query, url.fragment)
    )

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def repo(db_session) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(db_session)


@pytest.fixture
def mock_ocr():
    from unittest.mock import AsyncMock, MagicMock

    ocr = MagicMock()
    ocr.extract = AsyncMock()
    return ocr


@pytest.fixture
def mock_storage(minio_container):
    storage = MinioStorage()
    return storage


class TestWorkerEndToEnd:
    async def test_document_create_and_retrieve(self, repo, db_session):
        doc_id = uuid.uuid4()
        now = datetime.now(UTC)
        doc = Document(
            id=doc_id,
            type=DocumentType.INVOICE,
            region="AR",
            status=DocumentStatus.PENDING,
            media_type=MediaType.JPEG,
            image_key=f"{doc_id}.jpg",
            parsed_data=None,
            validation_result=None,
            error_detail=None,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc)

        retrieved = await repo.get_by_id(doc_id)
        assert retrieved is not None
        assert retrieved.id == doc_id
        assert retrieved.status == DocumentStatus.PENDING

    async def test_status_update_flow(self, repo, db_session):
        doc_id = uuid.uuid4()
        now = datetime.now(UTC)
        doc = Document(
            id=doc_id,
            type=DocumentType.INVOICE,
            region="AR",
            status=DocumentStatus.PENDING,
            media_type=MediaType.JPEG,
            image_key=f"{doc_id}.jpg",
            parsed_data=None,
            validation_result=None,
            error_detail=None,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc)

        await repo.update_status(doc_id, DocumentStatus.OCR_IN_PROGRESS)
        retrieved = await repo.get_by_id(doc_id)
        assert retrieved.status == DocumentStatus.OCR_IN_PROGRESS

        await repo.update_status(doc_id, DocumentStatus.COMPLETED)
        retrieved = await repo.get_by_id(doc_id)
        assert retrieved.status == DocumentStatus.COMPLETED
        assert retrieved.parsed_data is None

    async def test_update_parsed_data_persists(self, repo, db_session):
        doc_id = uuid.uuid4()
        now = datetime.now(UTC)
        doc = Document(
            id=doc_id,
            type=DocumentType.INVOICE,
            region="AR",
            status=DocumentStatus.PENDING,
            media_type=MediaType.JPEG,
            image_key=f"{doc_id}.jpg",
            parsed_data=None,
            validation_result=None,
            error_detail=None,
            created_at=now,
            updated_at=now,
        )
        await repo.create(doc)

        parsed = ParsedData(raw_text="Total: 1500.00", confidence=0.95, fields={"total": "1500.00"})
        await repo.update_parsed_data(doc_id, parsed, None)

        retrieved = await repo.get_by_id(doc_id)
        assert retrieved.parsed_data is not None
        assert retrieved.parsed_data.fields["total"] == "1500.00"

    async def test_list_documents_with_filters(self, repo, db_session):
        for _i in range(3):
            doc_id = uuid.uuid4()
            now = datetime.now(UTC)
            doc = Document(
                id=doc_id,
                type=DocumentType.INVOICE,
                region="AR",
                status=DocumentStatus.PENDING,
                media_type=MediaType.JPEG,
                image_key=f"{doc_id}.jpg",
                parsed_data=None,
                validation_result=None,
                error_detail=None,
                created_at=now,
                updated_at=now,
            )
            await repo.create(doc)

        docs, total = await repo.list_documents(page=1, size=10)
        assert total == 3
        assert len(docs) == 3

        docs, total = await repo.list_documents(status=DocumentStatus.PENDING, page=1, size=10)
        assert total == 3
