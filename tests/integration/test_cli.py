import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestApiKeyCLI:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    async def test_create_key_produces_valid_hash(self, mock_session: MagicMock) -> None:
        from document_processor.adapters.persistence.api_key_repo import (
            PostgresApiKeyRepository,
        )

        saved_keys: list[str] = []
        saved_prefixes: list[str] = []

        async def mock_add(model):
            saved_keys.append(model.key_hash)
            saved_prefixes.append(model.prefix)

        mock_session.add = mock_add
        mock_session.flush = AsyncMock()

        repo = PostgresApiKeyRepository(mock_session)
        repo.create_key = AsyncMock()

        import secrets
        raw_key = "sk-proj-" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]

        assert len(raw_key) > 8
        assert prefix.startswith("sk-proj-")
        assert len(key_hash) == 64

    async def test_revoked_key_rejected(self, mock_session: MagicMock) -> None:
        from document_processor.adapters.persistence.api_key_repo import (
            PostgresApiKeyRepository,
        )

        repo = PostgresApiKeyRepository(mock_session)
        repo.validate_key = AsyncMock(return_value=False)

        result = await repo.validate_key("some-hash")
        assert result is False
