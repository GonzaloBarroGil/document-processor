import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from document_processor.core.config import settings
from document_processor.core.logging import setup_logging
from document_processor.domain.services.storage_lifecycle import StorageLifecycleService
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.adapters.storage.minio import MinioStorage

logger = logging.getLogger(__name__)


async def _run_lifecycle() -> None:
    setup_logging()

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    storage = MinioStorage()

    async with session_factory() as session:
        repo = PostgresDocumentRepository(session)
        service = StorageLifecycleService(repository=repo, storage=storage)
        expired = await service.evaluate()

        if expired:
            logger.info("Expired %d images", len(expired))
        else:
            logger.info("No images expired")


def main() -> None:
    asyncio.run(_run_lifecycle())
