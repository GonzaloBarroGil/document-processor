from abc import ABC, abstractmethod


class ApiKeyRepositoryPort(ABC):
    @abstractmethod
    async def validate_key(self, key_hash: str) -> bool:
        ...
