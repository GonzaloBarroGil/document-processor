from abc import ABC, abstractmethod
from uuid import UUID

from document_processor.domain.models.user import User


class AuthPort(ABC):
    """Persistence port for the auth domain (human users)."""

    @abstractmethod
    async def get_user_by_username(self, username: str) -> User | None:
        """Return the user with the given username, or None if absent."""
        ...

    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Return the user with the given id, or None if absent."""
        ...

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Persist and return a newly created user."""
        ...
