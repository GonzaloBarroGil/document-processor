import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.core.config import settings
from document_processor.domain.models.document import DocumentStatus
from document_processor.adapters.persistence.postgresql.models import DocumentModel

logger = logging.getLogger(__name__)


async def poll_queue(
    session_factory, worker_id: str, process_fn, stop_event: asyncio.Event
) -> None:
    while not stop_event.is_set():
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
        .values(locked_by=worker_id, locked_at=datetime.now(timezone.utc))
    )
    await session.execute(lock_stmt)
    await session.commit()

    return doc
