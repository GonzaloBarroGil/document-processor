from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from document_processor.adapters.persistence.api_key_repo import (
    PostgresApiKeyRepository,
)
from document_processor.domain.models.api_key import ApiKey


def _make_api_key() -> ApiKey:
    return ApiKey(
        prefix="abcd1234",
        hash="0" * 64,
        label="billing",
        created_at=datetime.now(UTC),
        revoked=False,
    )


class TestPostgresApiKeyRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.execute = AsyncMock()
        s.add = MagicMock()
        s.flush = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresApiKeyRepository:
        return PostgresApiKeyRepository(session)

    async def test_create(self, repo: PostgresApiKeyRepository, session: MagicMock) -> None:
        api_key = _make_api_key()

        result = await repo.create(api_key)

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.prefix == api_key.prefix

    async def test_list_keys(self, repo: PostgresApiKeyRepository, session: MagicMock) -> None:
        model = MagicMock()
        model.prefix = "abcd1234"
        model.key_hash = "0" * 64
        model.label = "billing"
        model.created_at = datetime.now(UTC)
        model.revoked = False
        session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[model])))
            )
        )

        keys = await repo.list_keys()

        assert len(keys) == 1
        assert keys[0].prefix == "abcd1234"

    async def test_revoke_found(self, repo: PostgresApiKeyRepository, session: MagicMock) -> None:
        result = MagicMock()
        result.rowcount = 1
        session.execute = AsyncMock(return_value=result)

        revoked = await repo.revoke("abcd1234")

        assert revoked is True

    async def test_revoke_missing(self, repo: PostgresApiKeyRepository, session: MagicMock) -> None:
        result = MagicMock()
        result.rowcount = 0
        session.execute = AsyncMock(return_value=result)

        revoked = await repo.revoke("unknown")

        assert revoked is False
