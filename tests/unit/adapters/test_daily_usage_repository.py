from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from document_processor.adapters.persistence.postgresql.daily_usage_repository import (
    PostgresDailyUsageRepository,
)


class TestPostgresDailyUsageRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.execute = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresDailyUsageRepository:
        return PostgresDailyUsageRepository(session)

    async def test_increment(self, repo: PostgresDailyUsageRepository, session: MagicMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=5)))

        result = await repo.increment(date(2026, 1, 1), "global")

        assert result == 5
        session.execute.assert_called_once()

    async def test_get_existing(
        self, repo: PostgresDailyUsageRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=7))
        )

        result = await repo.get(date(2026, 1, 1), "global")

        assert result == 7

    async def test_get_missing(
        self, repo: PostgresDailyUsageRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        result = await repo.get(date(2026, 1, 1), "global")

        assert result == 0
