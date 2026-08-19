from abc import ABC, abstractmethod


class ApiKeyRepositoryPort(ABC):
    """Port for validating API keys against persistence."""

    @abstractmethod
    async def validate_key(self, key_hash: str) -> bool:
        """Return whether the given key hash is valid and not revoked."""
        ...
