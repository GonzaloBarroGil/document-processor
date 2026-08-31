import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from document_processor.adapters.persistence.api_key_repo import PostgresApiKeyRepository
from document_processor.core.config import settings
from document_processor.core.errors import ApiKeyNotFoundError
from document_processor.domain.services.api_key_service import ApiKeyService


async def create_key(label: str) -> None:
    """Create and persist a new API key with the given label."""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    async with session_factory() as session:
        service = ApiKeyService(PostgresApiKeyRepository(session))
        created = await service.create_key(label or None)
        await session.commit()

    print("API Key created (save it now — not shown again):")
    print(f"  Key:   {created.key}")
    print(f"  Label: {created.label or ''}")


async def list_keys() -> None:
    """List persisted API keys with their revocation status."""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    async with session_factory() as session:
        service = ApiKeyService(PostgresApiKeyRepository(session))
        keys = await service.list_keys()

    for key in keys:
        status = "REVOKED" if key.revoked else "ACTIVE"
        print(f"  [{status}] {key.prefix}...  {key.label or ''}  ({key.created_at})")


async def revoke_key(prefix: str) -> None:
    """Revoke the API key matching the given prefix."""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine)

    async with session_factory() as session:
        service = ApiKeyService(PostgresApiKeyRepository(session))
        try:
            await service.revoke(prefix)
            await session.commit()
        except ApiKeyNotFoundError:
            print(f"No key found with prefix {prefix}")
            return

    print(f"Key {prefix}... revoked")


def main() -> None:
    """CLI entry point for managing API keys."""
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
