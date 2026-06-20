from abc import ABC, abstractmethod


class StoragePort(ABC):
    @abstractmethod
    async def store(self, key: str, data: bytes, content_type: str) -> None:
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> bytes | None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def usage_pct(self) -> float:
        ...
