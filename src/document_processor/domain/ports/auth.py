from abc import ABC, abstractmethod
from uuid import UUID

from document_processor.domain.models.user import User


class AuthPort(ABC):
    @abstractmethod
    async def get_user_by_username(self, username: str) -> User | None:
        ...

    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    async def create_user(self, user: User) -> User:
        ...
