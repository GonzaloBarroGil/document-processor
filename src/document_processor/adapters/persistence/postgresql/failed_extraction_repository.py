from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import FailedExtractionModel
from document_processor.domain.ports.failed_extraction import FailedExtractionPort


class PostgresFailedExtractionRepository(FailedExtractionPort):
    """PostgreSQL-backed implementation of the failed-extraction port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_failure(self, document_id: UUID, error: str) -> None:
        """Record (or update) a failed-extraction entry with retry accounting."""
        stmt = (
            select(FailedExtractionModel)
            .where(FailedExtractionModel.document_id == document_id)
            .order_by(FailedExtractionModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            self._session.add(
                FailedExtractionModel(
                    document_id=document_id,
                    retry_count=1,
                    last_error=error,
                )
            )
        else:
            model.retry_count += 1
            model.last_error = error
            model.updated_at = datetime.now(UTC)

        await self._session.flush()
