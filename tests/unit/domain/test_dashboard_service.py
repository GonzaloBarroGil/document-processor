from unittest.mock import AsyncMock, MagicMock

import pytest

from document_processor.domain.services.dashboard_service import DashboardService


class TestDashboardService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, repo: MagicMock) -> DashboardService:
        return DashboardService(repository=repo)

    async def test_summary_combines_counts_and_recent(
        self, service: DashboardService, repo: MagicMock
    ) -> None:
        repo.count_by_status = AsyncMock(return_value={"COMPLETED": 5, "PENDING": 2})
        repo.list_documents = AsyncMock(return_value=([], 0))

        summary = await service.summary()

        assert summary.counts == {"COMPLETED": 5, "PENDING": 2}
        assert summary.recent == []
        repo.count_by_status.assert_called_once()
        repo.list_documents.assert_called_once_with(page=1, size=10)
