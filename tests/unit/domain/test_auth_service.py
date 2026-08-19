from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from document_processor.core.config import settings
from document_processor.core.errors import InvalidCredentialsError, InvalidTokenError
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


def _make_user(password: str = "s3cret") -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="alice",
        password_hash=PasswordHasher().hash(password),
        role=UserRole.REVIEWER,
        created_at=now,
        updated_at=now,
    )


class TestAuthService:
    @pytest.fixture
    def users(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def refresh_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, users: MagicMock, refresh_repo: MagicMock) -> AuthService:
        return AuthService(
            user_repository=users,
            refresh_token_repository=refresh_repo,
            tokens=TokenService(),
            passwords=PasswordHasher(),
        )

    async def test_authenticate_success(
        self, service: AuthService, users: MagicMock, refresh_repo: MagicMock
    ) -> None:
        user = _make_user()
        users.get_user_by_username = AsyncMock(return_value=user)
        refresh_repo.save = AsyncMock()

        pair = await service.authenticate("alice", "s3cret")

        assert pair.access_token
        assert pair.refresh_token
        assert pair.expires_in == settings.access_token_ttl_seconds
        refresh_repo.save.assert_called_once()

    async def test_authenticate_wrong_password(
        self, service: AuthService, users: MagicMock
    ) -> None:
        users.get_user_by_username = AsyncMock(return_value=_make_user())

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("alice", "wrong")

    async def test_authenticate_unknown_user(self, service: AuthService, users: MagicMock) -> None:
        users.get_user_by_username = AsyncMock(return_value=None)

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("alice", "s3cret")

    async def test_refresh_rotates_token(
        self, service: AuthService, users: MagicMock, refresh_repo: MagicMock
    ) -> None:
        user = _make_user()
        users.get_user_by_username = AsyncMock(return_value=user)
        users.get_user_by_id = AsyncMock(return_value=user)
        refresh_repo.save = AsyncMock()
        refresh_repo.is_active = AsyncMock(return_value=True)
        refresh_repo.revoke = AsyncMock()

        pair = await service.authenticate("alice", "s3cret")

        new_pair = await service.refresh(pair.refresh_token)

        assert new_pair.refresh_token != pair.refresh_token
        assert new_pair.access_token != pair.access_token
        refresh_repo.revoke.assert_called_once()

    async def test_refresh_inactive_token(
        self, service: AuthService, users: MagicMock, refresh_repo: MagicMock
    ) -> None:
        user = _make_user()
        users.get_user_by_username = AsyncMock(return_value=user)
        refresh_repo.save = AsyncMock()

        pair = await service.authenticate("alice", "s3cret")

        refresh_repo.is_active = AsyncMock(return_value=False)

        with pytest.raises(InvalidTokenError):
            await service.refresh(pair.refresh_token)

    async def test_refresh_unknown_user(
        self, service: AuthService, users: MagicMock, refresh_repo: MagicMock
    ) -> None:
        user = _make_user()
        users.get_user_by_username = AsyncMock(return_value=user)
        refresh_repo.save = AsyncMock()

        pair = await service.authenticate("alice", "s3cret")

        refresh_repo.is_active = AsyncMock(return_value=True)
        users.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidTokenError):
            await service.refresh(pair.refresh_token)
