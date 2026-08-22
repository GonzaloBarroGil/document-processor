from abc import ABC, abstractmethod

from document_processor.domain.models.api_key import ApiKey


class ApiKeyRepositoryPort(ABC):
    """Port for validating and managing API keys against persistence."""

    @abstractmethod
    async def validate_key(self, key_hash: str) -> bool:
        """Return whether the given key hash is valid and not revoked."""
        ...

    @abstractmethod
    async def create(self, api_key: ApiKey) -> ApiKey:
        """Persist and return a newly created API key."""
        ...

    @abstractmethod
    async def list_keys(self) -> list[ApiKey]:
        """Return all API keys, most recent first."""
        ...

    @abstractmethod
    async def revoke(self, prefix: str) -> bool:
        """Revoke the API key with the given prefix; return whether one was revoked."""
        ...
