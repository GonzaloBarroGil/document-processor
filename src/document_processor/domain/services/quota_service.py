from datetime import UTC, date, datetime, timedelta

from document_processor.core.config import settings
from document_processor.core.errors import DailyQuotaExceededError
from document_processor.domain.ports.daily_usage import DailyUsageRepositoryPort


def seconds_until_midnight_utc(now: datetime | None = None) -> int:
    """Return the number of seconds until the next UTC midnight."""
    now = now or datetime.now(UTC)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((midnight - now).total_seconds())


class QuotaService:
    """Enforces the daily ingestion quota per scope (global and per-key)."""

    def __init__(self, usage_repository: DailyUsageRepositoryPort) -> None:
        self._usage_repository = usage_repository

    async def check_and_increment(self, scope: str) -> None:
        """Reserve a slot for the given scope, raising if the daily cap is exceeded."""
        count = await self._usage_repository.increment(self._today(), scope)
        if count > settings.daily_document_cap:
            raise DailyQuotaExceededError(scope, settings.daily_document_cap)

    async def is_exceeded(self, scope: str) -> bool:
        """Return True if the given scope is already over the daily cap."""
        count = await self._usage_repository.get(self._today(), scope)
        return count > settings.daily_document_cap

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()
