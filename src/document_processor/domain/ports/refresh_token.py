from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class RefreshTokenRepositoryPort(ABC):
    """Persistence port for rotating refresh tokens."""

    @abstractmethod
    async def save(self, token_hash: str, user_id: UUID, expires_at: datetime) -> None:
        """Persist the hash of a newly issued refresh token."""
        ...

    @abstractmethod
    async def is_active(self, token_hash: str) -> bool:
        """Return True if the token is known and has not been revoked."""
        ...

    @abstractmethod
    async def revoke(self, token_hash: str) -> None:
        """Mark the refresh token as revoked."""
        ...
