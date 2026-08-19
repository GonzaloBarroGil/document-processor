from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import ApiKeyModel
from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort


class PostgresApiKeyRepository(ApiKeyRepositoryPort):
    """PostgreSQL-backed implementation of the API key repository port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def validate_key(self, key_hash: str) -> bool:
        """Return whether the given key hash identifies an active API key."""
        stmt = select(ApiKeyModel).where(
            ApiKeyModel.key_hash == key_hash,
            ApiKeyModel.revoked == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
