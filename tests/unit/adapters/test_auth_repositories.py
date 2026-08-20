from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from document_processor.adapters.persistence.postgresql.models import (
    model_to_user,
    user_to_model,
)
from document_processor.adapters.persistence.postgresql.refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from document_processor.adapters.persistence.postgresql.user_repository import (
    PostgresUserRepository,
)
from document_processor.domain.models.user import User, UserRole


def _make_user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="alice",
        password_hash="argon2id-hash",
        role=UserRole.REVIEWER,
        created_at=now,
        updated_at=now,
    )


class TestUserConversion:
    def test_roundtrip(self) -> None:
        user = _make_user()
        result = model_to_user(user_to_model(user))
        assert result.id == user.id
        assert result.username == user.username
        assert result.role == user.role
        assert result.password_hash == user.password_hash


class TestPostgresUserRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.execute = AsyncMock()
        s.add = MagicMock()
        s.flush = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresUserRepository:
        return PostgresUserRepository(session)

    async def test_get_by_username_found(
        self, repo: PostgresUserRepository, session: MagicMock
    ) -> None:
        user = _make_user()
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user_to_model(user)))
        )

        result = await repo.get_user_by_username("alice")

        assert result is not None
        assert result.id == user.id

    async def test_get_by_username_not_found(
        self, repo: PostgresUserRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        result = await repo.get_user_by_username("alice")

        assert result is None

    async def test_get_by_id_found(self, repo: PostgresUserRepository, session: MagicMock) -> None:
        user = _make_user()
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user_to_model(user)))
        )

        result = await repo.get_user_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    async def test_create_user(self, repo: PostgresUserRepository, session: MagicMock) -> None:
        user = _make_user()

        result = await repo.create_user(user)

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.id == user.id


class TestPostgresRefreshTokenRepository:
    @pytest.fixture
    def session(self) -> MagicMock:
        s = MagicMock()
        s.execute = AsyncMock()
        s.add = MagicMock()
        s.flush = AsyncMock()
        return s

    @pytest.fixture
    def repo(self, session: MagicMock) -> PostgresRefreshTokenRepository:
        return PostgresRefreshTokenRepository(session)

    async def test_save(self, repo: PostgresRefreshTokenRepository, session: MagicMock) -> None:
        await repo.save("hash", uuid4(), datetime.now(UTC) + timedelta(days=1))

        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_is_active_true(
        self, repo: PostgresRefreshTokenRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=MagicMock()))
        )

        assert await repo.is_active("hash") is True

    async def test_is_active_false(
        self, repo: PostgresRefreshTokenRepository, session: MagicMock
    ) -> None:
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        assert await repo.is_active("hash") is False

    async def test_revoke(self, repo: PostgresRefreshTokenRepository, session: MagicMock) -> None:
        session.execute = AsyncMock()

        await repo.revoke("hash")

        session.execute.assert_called_once()
