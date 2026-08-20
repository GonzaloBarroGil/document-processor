from abc import ABC, abstractmethod
from datetime import date


class DailyUsageRepositoryPort(ABC):
    """Port for tracking daily ingestion usage counters."""

    @abstractmethod
    async def increment(self, usage_date: date, scope: str) -> int:
        """Atomically increment and return the usage count for the given date/scope."""
        ...

    @abstractmethod
    async def get(self, usage_date: date, scope: str) -> int:
        """Return the current usage count for the given date/scope."""
        ...
