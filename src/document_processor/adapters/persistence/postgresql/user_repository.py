from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import (
    UserModel,
    model_to_user,
    user_to_model,
)
from document_processor.domain.models.user import User
from document_processor.domain.ports.auth import AuthPort


class PostgresUserRepository(AuthPort):
    """PostgreSQL-backed implementation of the auth (user) port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_username(self, username: str) -> User | None:
        """Return the user with the given username, or None if absent."""
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_user(model) if model is not None else None

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Return the user with the given id, or None if absent."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_user(model) if model is not None else None

    async def create_user(self, user: User) -> User:
        """Persist and return a newly created user."""
        model = user_to_model(user)
        self._session.add(model)
        await self._session.flush()
        return user
