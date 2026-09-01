import asyncio
import logging
import os
import signal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from document_processor.adapters.ocr.easyocr import EasyOCRAdapter
from document_processor.adapters.ocr.paddle import PaddleOCRAdapter
from document_processor.adapters.persistence.postgresql.daily_usage_repository import (
    PostgresDailyUsageRepository,
)
from document_processor.adapters.persistence.postgresql.models import (
    DocumentModel,
    model_to_document,
)
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.adapters.persistence.queue import poll_queue
from document_processor.adapters.storage.minio import MinioStorage
from document_processor.adapters.validators.registry import ValidatorRegistry
from document_processor.core.config import settings
from document_processor.core.logging import setup_logging
from document_processor.domain.ports.ocr import OCRPort
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.quota_service import QuotaService

logger = logging.getLogger(__name__)


async def _process_document(
    session_factory: async_sessionmaker[AsyncSession],
    storage: MinioStorage,
    ocr: OCRPort,
    validators: dict[str, RegionValidatorPort],
    doc: DocumentModel,
) -> None:
    """Run the OCR pipeline for one claimed document in a fresh, committed session."""
    domain_doc = model_to_document(doc)
    async with session_factory() as session:
        service = DocumentService(
            repository=PostgresDocumentRepository(session),
            storage=storage,
            ocr=ocr,
            validator_registry=validators,
        )
        await service.process_document(domain_doc)
        await session.commit()


async def _run_worker() -> None:
    setup_logging()

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    validator_registry = ValidatorRegistry()
    validator_registry.discover()
    validators = dict(validator_registry._validators)

    storage = MinioStorage()
    ocr_cls = PaddleOCRAdapter if settings.ocr_primary_engine == "paddle" else EasyOCRAdapter
    ocr_adapter = ocr_cls()

    worker_id = f"worker-{os.getpid()}"
    logger.info("Worker %s started", worker_id)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    async def _global_quota_exceeded() -> bool:
        async with session_factory() as session:
            quota = QuotaService(PostgresDailyUsageRepository(session))
            return await quota.is_exceeded("global")

    await poll_queue(
        session_factory,
        worker_id,
        lambda doc: _process_document(session_factory, storage, ocr_adapter, validators, doc),
        stop_event,
        quota_check=_global_quota_exceeded,
    )

    logger.info("Worker %s stopped", worker_id)


def main() -> None:
    """CLI entry point for running the OCR processing worker."""
    asyncio.run(_run_worker())
