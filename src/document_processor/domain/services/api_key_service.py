import hashlib
import secrets
from datetime import UTC, datetime

from document_processor.core.errors import ApiKeyNotFoundError
from document_processor.domain.models.api_key import ApiKey, CreatedApiKey
from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort


def generate_api_key() -> tuple[str, str, str]:
    """Generate a raw API key, its unique prefix, and its SHA-256 hash."""
    token = secrets.token_urlsafe(32)
    raw = f"sk-proj-{token}"
    prefix = token[:8]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash


class ApiKeyService:
    """Issues, lists, and revokes machine-client API keys."""

    def __init__(self, repository: ApiKeyRepositoryPort) -> None:
        self._repository = repository

    async def create_key(self, label: str | None) -> CreatedApiKey:
        """Issue a new API key and return its one-time raw value."""
        raw, prefix, key_hash = generate_api_key()
        await self._repository.create(
            ApiKey(
                prefix=prefix,
                hash=key_hash,
                label=label,
                created_at=datetime.now(UTC),
                revoked=False,
            )
        )
        return CreatedApiKey(key=raw, prefix=prefix, label=label)

    async def list_keys(self) -> list[ApiKey]:
        """Return all API keys, most recent first."""
        return await self._repository.list_keys()

    async def revoke(self, prefix: str) -> None:
        """Revoke the API key with the given prefix."""
        revoked = await self._repository.revoke(prefix)
        if not revoked:
            raise ApiKeyNotFoundError(prefix)
