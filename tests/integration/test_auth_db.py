from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from document_processor.adapters.persistence.postgresql.models import Base
from document_processor.adapters.persistence.postgresql.refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from document_processor.adapters.persistence.postgresql.user_repository import (
    PostgresUserRepository,
)
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


@pytest.fixture(scope="module")
def db_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture
async def session_factory(db_container):
    url = urlparse(db_container.get_connection_url())
    db_url = urlunparse(
        ("postgresql+asyncpg", url.netloc, url.path, url.params, url.query, url.fragment)
    )
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine)
    yield factory

    await engine.dispose()


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


class TestAuthFlow:
    async def test_login_refresh_me_logout(self, session_factory) -> None:
        user = _make_user()

        async with session_factory() as session:
            users = PostgresUserRepository(session)
            refresh = PostgresRefreshTokenRepository(session)
            auth = AuthService(
                user_repository=users,
                refresh_token_repository=refresh,
                tokens=TokenService(),
                passwords=PasswordHasher(),
            )

            await users.create_user(user)

            pair = await auth.authenticate("alice", "s3cret")
            assert pair.access_token
            assert pair.refresh_token

            me = await auth.current_user(pair.access_token)
            assert me.id == user.id
            assert me.username == "alice"

            new_pair = await auth.refresh(pair.refresh_token)
            assert new_pair.access_token != pair.access_token
            assert new_pair.refresh_token != pair.refresh_token

            await auth.logout(new_pair.refresh_token)
            assert await refresh.is_active(TokenService.hash_token(new_pair.refresh_token)) is False

    async def test_authenticate_wrong_password(self, session_factory) -> None:
        from document_processor.core.errors import InvalidCredentialsError

        user = _make_user()

        async with session_factory() as session:
            users = PostgresUserRepository(session)
            refresh = PostgresRefreshTokenRepository(session)
            auth = AuthService(
                user_repository=users,
                refresh_token_repository=refresh,
                tokens=TokenService(),
                passwords=PasswordHasher(),
            )

            await users.create_user(user)

            with pytest.raises(InvalidCredentialsError):
                await auth.authenticate("alice", "wrong")
