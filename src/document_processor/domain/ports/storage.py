from abc import ABC, abstractmethod


class StoragePort(ABC):
    """Port for storing and retrieving document image bytes."""

    @abstractmethod
    async def store(self, key: str, data: bytes, content_type: str) -> None:
        """Store object bytes under the given key."""
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> bytes | None:
        """Return the object bytes for the given key, or None if absent."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the object stored under the given key."""
        ...

    @abstractmethod
    async def usage_pct(self) -> float:
        """Return storage usage as a percentage of the configured quota."""
        ...
