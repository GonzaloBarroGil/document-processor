from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from document_processor.core.config import settings
from document_processor.core.errors import DailyQuotaExceededError
from document_processor.domain.services.quota_service import (
    QuotaService,
    seconds_until_midnight_utc,
)


class TestQuotaService:
    @pytest.fixture
    def usage(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, usage: MagicMock) -> QuotaService:
        return QuotaService(usage_repository=usage)

    async def test_check_and_increment_under_cap(
        self, service: QuotaService, usage: MagicMock
    ) -> None:
        usage.increment = AsyncMock(return_value=settings.daily_document_cap)

        await service.check_and_increment("global")

        usage.increment.assert_called_once()

    async def test_check_and_increment_over_cap(
        self, service: QuotaService, usage: MagicMock
    ) -> None:
        usage.increment = AsyncMock(return_value=settings.daily_document_cap + 1)

        with pytest.raises(DailyQuotaExceededError):
            await service.check_and_increment("global")

    async def test_is_exceeded_true(self, service: QuotaService, usage: MagicMock) -> None:
        usage.get = AsyncMock(return_value=settings.daily_document_cap + 1)

        assert await service.is_exceeded("global") is True

    async def test_is_exceeded_false(self, service: QuotaService, usage: MagicMock) -> None:
        usage.get = AsyncMock(return_value=settings.daily_document_cap)

        assert await service.is_exceeded("global") is False


class TestSecondsUntilMidnight:
    def test_returns_seconds_until_next_midnight(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

        assert seconds_until_midnight_utc(now) == 12 * 3600
