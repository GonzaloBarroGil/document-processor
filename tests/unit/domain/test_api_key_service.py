from unittest.mock import AsyncMock, MagicMock

import pytest

from document_processor.core.errors import ApiKeyNotFoundError
from document_processor.domain.services.api_key_service import (
    ApiKeyService,
    generate_api_key,
)


def test_generate_api_key_shape() -> None:
    raw, prefix, key_hash = generate_api_key()

    assert raw.startswith("sk-proj-")
    assert len(prefix) == 8
    assert len(key_hash) == 64


class TestApiKeyService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, repo: MagicMock) -> ApiKeyService:
        return ApiKeyService(repository=repo)

    async def test_create_key_stores_hash(self, service: ApiKeyService, repo: MagicMock) -> None:
        repo.create = AsyncMock()

        created = await service.create_key("billing")

        assert created.key.startswith("sk-proj-")
        assert created.prefix == created.key[8:16]
        assert created.label == "billing"
        repo.create.assert_called_once()

    async def test_list_keys_delegates(self, service: ApiKeyService, repo: MagicMock) -> None:
        repo.list_keys = AsyncMock(return_value=[])

        keys = await service.list_keys()

        assert keys == []
        repo.list_keys.assert_called_once()

    async def test_revoke_delegates(self, service: ApiKeyService, repo: MagicMock) -> None:
        repo.revoke = AsyncMock(return_value=True)

        await service.revoke("abcd1234")

        repo.revoke.assert_called_once_with("abcd1234")

    async def test_revoke_not_found(self, service: ApiKeyService, repo: MagicMock) -> None:
        repo.revoke = AsyncMock(return_value=False)

        with pytest.raises(ApiKeyNotFoundError):
            await service.revoke("abcd1234")
