from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


def _make_user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="alice",
        password_hash=PasswordHasher().hash("s3cret"),
        role=UserRole.REVIEWER,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def client() -> TestClient:
    user = _make_user()

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

    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(return_value=False)

    user_repo = MagicMock()
    user_repo.get_user_by_username = AsyncMock(return_value=user)
    user_repo.get_user_by_id = AsyncMock(return_value=user)
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
        api_key_repository=api_key_repo,
        validator_registry={},
        auth_service=auth_service,
    )
    return TestClient(app)


def _login(client: TestClient) -> dict:
    response = client.post("/api/v1/auth/login", json={"username": "alice", "password": "s3cret"})
    assert response.status_code == 200
    return response.json()


class TestLogin:
    def test_login_success(self, client: TestClient) -> None:
        data = _login(client)
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "wrong"}
        )
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client: TestClient) -> None:
        login = _login(client)
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert response.status_code == 200
        assert response.json()["access_token"] != login["access_token"]

    def test_refresh_invalid_token(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": "bogus"})
        assert response.status_code == 401


class TestMe:
    def test_me_success(self, client: TestClient) -> None:
        login = _login(client)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "alice"
        assert data["role"] == "REVIEWER"
        assert data["id"]

    def test_me_missing_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client: TestClient) -> None:
        login = _login(client)
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {login['access_token']}"},
            json={"refresh_token": login["refresh_token"]},
        )
        assert response.status_code == 204

    def test_logout_without_bearer(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
