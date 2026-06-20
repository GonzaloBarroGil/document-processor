import logging
from datetime import UTC, datetime, timedelta

from document_processor.core.config import settings
from document_processor.domain.models.document import DocumentStatus
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)
from document_processor.domain.ports.storage import StoragePort

logger = logging.getLogger(__name__)


class StorageLifecycleService:
    def __init__(
        self, repository: DocumentRepositoryPort, storage: StoragePort
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def evaluate(self) -> list[str]:
        usage_pct = await self._storage.usage_pct()
        expired_keys: list[str] = []

        if usage_pct < settings.storage_high_watermark_pct:
            logger.debug("Storage usage %.1f%% below watermark", usage_pct)
            return []

        if usage_pct >= settings.storage_critical_pct:
            expired_keys = await self._expire_documents(
                settings.storage_expire_critical_days,
                include_failed=True,
            )
        elif usage_pct >= settings.storage_high_watermark_pct:
            expired_keys = await self._expire_documents(
                settings.storage_expire_completed_days,
                include_failed=False,
            )

        return expired_keys

    async def _expire_documents(
        self, days: int, include_failed: bool
    ) -> list[str]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        statuses = [DocumentStatus.COMPLETED]
        if include_failed:
            statuses.append(DocumentStatus.VALIDATION_FAILED)

        expired_keys: list[str] = []

        for status in statuses:
            documents, _ = await self._repository.list_documents(
                status=status, page=1, size=1000
            )

            for doc in documents:
                if doc.created_at <= cutoff:
                    await self._storage.delete(doc.image_key)
                    await self._repository.update_status(
                        doc.id, DocumentStatus.IMAGE_EXPIRED
                    )
                    expired_keys.append(doc.image_key)
                    logger.info("Expired image for document %s", doc.id)

        return expired_keys
