from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import DailyUsageModel
from document_processor.domain.ports.daily_usage import DailyUsageRepositoryPort


class PostgresDailyUsageRepository(DailyUsageRepositoryPort):
    """PostgreSQL-backed implementation of the daily usage port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment(self, usage_date: date, scope: str) -> int:
        """Atomically increment and return the usage count for the given date/scope."""
        stmt = (
            insert(DailyUsageModel)
            .values(usage_date=usage_date, scope=scope, count=1)
            .on_conflict_do_update(
                index_elements=["usage_date", "scope"],
                set_={"count": DailyUsageModel.count + 1},
            )
            .returning(DailyUsageModel.count)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get(self, usage_date: date, scope: str) -> int:
        """Return the current usage count for the given date/scope."""
        stmt = select(DailyUsageModel.count).where(
            DailyUsageModel.usage_date == usage_date,
            DailyUsageModel.scope == scope,
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one_or_none()
        return count if count is not None else 0
