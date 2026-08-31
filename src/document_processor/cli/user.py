import asyncio
import sys
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from document_processor.adapters.persistence.postgresql.user_repository import (
    PostgresUserRepository,
)
from document_processor.core.config import settings
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.password_hasher import PasswordHasher


async def create_user(username: str, role: str, password: str) -> None:
    """Create and persist a human user with an argon2id password hash."""
    try:
        parsed_role = UserRole(role.upper())
    except ValueError:
        print(f"Invalid role: {role} (use ADMIN or REVIEWER)")
        sys.exit(1)

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)
    hasher = PasswordHasher()

    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        username=username,
        password_hash=hasher.hash(password),
        role=parsed_role,
        created_at=now,
        updated_at=now,
    )

    async with session_factory() as session:
        repository = PostgresUserRepository(session)
        await repository.create_user(user)
        await session.commit()

    print(f"User created: {username} ({parsed_role.value})")


def main() -> None:
    """CLI entry point for managing human users."""
    if len(sys.argv) < 2:
        print("Usage: docproc-user create <username> <role> <password>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 5:
            print("Usage: docproc-user create <username> <role> <password>")
            sys.exit(1)
        username, role, password = sys.argv[2], sys.argv[3], sys.argv[4]
        asyncio.run(create_user(username, role, password))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
