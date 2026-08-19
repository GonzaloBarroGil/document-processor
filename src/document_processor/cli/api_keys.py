import hashlib
import secrets
import sys
from datetime import UTC
from typing import Any, cast

from sqlalchemy import CursorResult
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from document_processor.adapters.persistence.postgresql.models import ApiKeyModel
from document_processor.core.config import settings


def generate_key() -> tuple[str, str, str]:
    """Generate a new raw API key, its prefix, and SHA-256 hash."""
    raw = "sk-proj-" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:8]
    return raw, prefix, key_hash


async def create_key(label: str) -> None:
    """Create and persist a new API key with the given label."""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    raw, prefix, key_hash = generate_key()
    async with session_factory() as session:
        model = ApiKeyModel(prefix=prefix, key_hash=key_hash, label=label)
        session.add(model)
        await session.commit()

    print("API Key created (save it now — not shown again):")
    print(f"  Key:   {raw}")
    print(f"  Label: {label}")


async def list_keys() -> None:
    """List persisted API keys with their revocation status."""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    async with session_factory() as session:
        from sqlalchemy import select

        stmt = select(ApiKeyModel).order_by(ApiKeyModel.created_at.desc())
        result = await session.execute(stmt)
        keys = result.scalars().all()

        for k in keys:
            status = "REVOKED" if k.revoked else "ACTIVE"
            print(f"  [{status}] {k.prefix}...  {k.label or ''}  ({k.created_at})")


async def revoke_key(prefix: str) -> None:
    """Revoke the API key matching the given prefix."""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    async with session_factory() as session:
        from datetime import datetime

        from sqlalchemy import update

        stmt = (
            update(ApiKeyModel)
            .where(ApiKeyModel.prefix == prefix)
            .values(revoked=True, revoked_at=datetime.now(UTC))
        )
        result = cast(CursorResult[Any], await session.execute(stmt))
        await session.commit()

        if result.rowcount == 0:
            print(f"No key found with prefix {prefix}")
        else:
            print(f"Key {prefix}... revoked")


def main() -> None:
    """CLI entry point for managing API keys."""
    import asyncio

    if len(sys.argv) < 2:
        print("Usage: docproc-keys <create|list|revoke> [args]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        label = sys.argv[2] if len(sys.argv) > 2 else ""
        asyncio.run(create_key(label))
    elif command == "list":
        asyncio.run(list_keys())
    elif command == "revoke":
        if len(sys.argv) < 3:
            print("Usage: docproc-keys revoke <prefix>")
            sys.exit(1)
        asyncio.run(revoke_key(sys.argv[2]))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
