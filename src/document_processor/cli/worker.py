import asyncio
import logging
import os
import signal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from document_processor.core.config import settings
from document_processor.core.logging import setup_logging
from document_processor.domain.services.document_service import DocumentService
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.adapters.persistence.queue import poll_queue
from document_processor.adapters.storage.minio import MinioStorage
from document_processor.adapters.ocr.paddle import PaddleOCRAdapter
from document_processor.adapters.ocr.easyocr import EasyOCRAdapter
from document_processor.adapters.validators.registry import ValidatorRegistry

logger = logging.getLogger(__name__)


async def _process_document(service: DocumentService, doc) -> None:
    from document_processor.adapters.persistence.postgresql.models import (
        model_to_document,
    )

    domain_doc = model_to_document(doc)
    await service.process_document(domain_doc)


async def _run_worker() -> None:
    setup_logging()

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    validator_registry = ValidatorRegistry()
    validator_registry.discover()

    storage = MinioStorage()
    ocr_adapter = PaddleOCRAdapter() if settings.ocr_primary_engine == "paddle" else EasyOCRAdapter()

    async with session_factory() as session:
        repo = PostgresDocumentRepository(session)
        service = DocumentService(
            repository=repo,
            storage=storage,
            ocr=ocr_adapter,
            validator_registry={k: v for k, v in validator_registry._validators.items()},
        )

    worker_id = f"worker-{os.getpid()}"
    logger.info("Worker %s started", worker_id)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await poll_queue(session_factory, worker_id, lambda doc: _process_document(service, doc), stop_event)

    logger.info("Worker %s stopped", worker_id)


def main() -> None:
    asyncio.run(_run_worker())
