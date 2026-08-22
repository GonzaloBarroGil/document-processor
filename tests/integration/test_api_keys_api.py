from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.api_key_service import ApiKeyService
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


def _make_admin() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="admin",
        password_hash=PasswordHasher().hash("s3cret"),
        role=UserRole.ADMIN,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def client() -> TestClient:
    admin = _make_admin()

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_documents = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    repo.update_parsed_data = AsyncMock()
    storage = MagicMock()
    storage.store = AsyncMock()
    storage.retrieve = AsyncMock()
    document_service = DocumentService(
        repository=repo,
        storage=storage,
        ocr=MagicMock(),
        validator_registry={},
    )

    middleware_api_key_repo = MagicMock()
    middleware_api_key_repo.validate_key = AsyncMock(return_value=False)

    api_key_repo = MagicMock()
    api_key_repo.create = AsyncMock()
    api_key_repo.list_keys = AsyncMock(return_value=[])
    api_key_repo.revoke = AsyncMock(return_value=True)
    api_key_service = ApiKeyService(repository=api_key_repo)

    user_repo = MagicMock()
    user_repo.get_user_by_username = AsyncMock(return_value=admin)
    user_repo.get_user_by_id = AsyncMock(return_value=admin)
    refresh_repo = MagicMock()
    refresh_repo.save = AsyncMock()
    refresh_repo.is_active = AsyncMock(return_value=True)
    refresh_repo.revoke = AsyncMock()
    auth_service = AuthService(
        user_repository=user_repo,
        refresh_token_repository=refresh_repo,
        tokens=TokenService(),
        passwords=PasswordHasher(),
    )

    app = create_app(
        document_service=document_service,
        api_key_repository=middleware_api_key_repo,
        validator_registry={},
        auth_service=auth_service,
        api_key_service=api_key_service,
    )
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "s3cret"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestApiKeys:
    def test_create_api_key(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/api-keys",
            headers=_admin_headers(client),
            json={"label": "billing"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["key"].startswith("sk-proj-")
        assert data["prefix"]
        assert data["label"] == "billing"

    def test_list_api_keys(self, client: TestClient) -> None:
        response = client.get("/api/v1/api-keys", headers=_admin_headers(client))

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_revoke_api_key(self, client: TestClient) -> None:
        response = client.post("/api/v1/api-keys/abcd1234/revoke", headers=_admin_headers(client))

        assert response.status_code == 204

    def test_revoke_missing_api_key(self, client: TestClient) -> None:
        from document_processor.adapters.web.api.deps import get_api_key_service

        get_api_key_service()._repository.revoke = AsyncMock(return_value=False)

        response = client.post("/api/v1/api-keys/unknown/revoke", headers=_admin_headers(client))

        assert response.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/api-keys")

        assert response.status_code == 401
