from abc import ABC, abstractmethod
from typing import Optional


class StoragePort(ABC):
    @abstractmethod
    async def store(self, key: str, data: bytes, content_type: str) -> None:
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[bytes]:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def usage_pct(self) -> float:
        ...
