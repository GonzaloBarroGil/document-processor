from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import RefreshTokenModel
from document_processor.domain.ports.refresh_token import RefreshTokenRepositoryPort


class PostgresRefreshTokenRepository(RefreshTokenRepositoryPort):
    """PostgreSQL-backed implementation of the refresh token repository port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token_hash: str, user_id: UUID, expires_at: datetime) -> None:
        """Persist the hash of a newly issued refresh token."""
        model = RefreshTokenModel(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def is_active(self, token_hash: str) -> bool:
        """Return True if the token is known and has not been revoked."""
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash,
            RefreshTokenModel.revoked == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke(self, token_hash: str) -> None:
        """Mark the refresh token as revoked."""
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(revoked=True)
        )
        await self._session.execute(stmt)
