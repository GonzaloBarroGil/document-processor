from abc import ABC, abstractmethod
from uuid import UUID


class FailedExtractionPort(ABC):
    """Port for recording failed extractions in the dead-letter queue."""

    @abstractmethod
    async def record_failure(self, document_id: UUID, error: str) -> None:
        """Record (or update) a failed-extraction entry with retry accounting."""
        ...
