from document_processor.domain.models.dashboard import DashboardSummary
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)


class DashboardService:
    """Builds the processing summary for the dashboard."""

    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    async def summary(self) -> DashboardSummary:
        """Return counts by status plus the most recent documents."""
        counts = await self._repository.count_by_status()
        recent, _ = await self._repository.list_documents(page=1, size=10)
        return DashboardSummary(counts=counts, recent=recent)
