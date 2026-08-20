import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from document_processor.adapters.persistence.postgresql.models import DocumentModel
from document_processor.core.config import settings
from document_processor.domain.models.document import DocumentStatus

logger = logging.getLogger(__name__)


async def poll_queue(
    session_factory: async_sessionmaker[AsyncSession],
    worker_id: str,
    process_fn: Callable[[DocumentModel], Awaitable[None]],
    stop_event: asyncio.Event,
    quota_check: Callable[[], Awaitable[bool]] | None = None,
) -> None:
    """Continuously claim and process pending documents until the stop event is set."""
    while not stop_event.is_set():
        if quota_check is not None and await quota_check():
            await asyncio.sleep(settings.worker_poll_interval_seconds)
            continue

        async with session_factory() as session:
            try:
                doc = await _claim_pending(session, worker_id)
                if doc is None:
                    await asyncio.sleep(settings.worker_poll_interval_seconds)
                    continue

                await process_fn(doc)

            except Exception:
                logger.exception("Worker %s error processing document", worker_id)
                await asyncio.sleep(settings.worker_poll_interval_seconds)
            finally:
                await session.rollback()


async def _claim_pending(session: AsyncSession, worker_id: str) -> DocumentModel | None:
    stmt = (
        select(DocumentModel)
        .where(
            DocumentModel.status == DocumentStatus.PENDING.value,
            DocumentModel.locked_by.is_(None),
        )
        .order_by(DocumentModel.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if doc is None:
        return None

    lock_stmt = (
        update(DocumentModel)
        .where(DocumentModel.id == doc.id)
        .values(locked_by=worker_id, locked_at=datetime.now(UTC))
    )
    await session.execute(lock_stmt)
    await session.commit()

    return doc
