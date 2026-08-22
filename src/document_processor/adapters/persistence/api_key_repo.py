from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import ApiKeyModel
from document_processor.domain.models.api_key import ApiKey
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

    async def create(self, api_key: ApiKey) -> ApiKey:
        """Persist and return a newly created API key."""
        model = ApiKeyModel(
            prefix=api_key.prefix,
            key_hash=api_key.hash,
            label=api_key.label,
            created_at=api_key.created_at,
            revoked=api_key.revoked,
        )
        self._session.add(model)
        await self._session.flush()
        return api_key

    async def list_keys(self) -> list[ApiKey]:
        """Return all API keys, most recent first."""
        stmt = select(ApiKeyModel).order_by(ApiKeyModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [
            ApiKey(
                prefix=model.prefix,
                hash=model.key_hash,
                label=model.label,
                created_at=model.created_at,
                revoked=model.revoked,
            )
            for model in models
        ]

    async def revoke(self, prefix: str) -> bool:
        """Revoke the API key with the given prefix; return whether one was revoked."""
        stmt = (
            update(ApiKeyModel)
            .where(ApiKeyModel.prefix == prefix)
            .values(revoked=True, revoked_at=datetime.now(UTC))
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return result.rowcount > 0
