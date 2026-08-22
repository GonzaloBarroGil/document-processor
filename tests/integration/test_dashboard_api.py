from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.dashboard_service import DashboardService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


def _make_reviewer() -> User:
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
    user = _make_reviewer()

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

    dashboard_repo = MagicMock()
    dashboard_repo.count_by_status = AsyncMock(return_value={"COMPLETED": 3})
    dashboard_repo.list_documents = AsyncMock(return_value=([], 0))
    dashboard_service = DashboardService(repository=dashboard_repo)

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
        dashboard_service=dashboard_service,
    )
    return TestClient(app)


def _bearer(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "alice", "password": "s3cret"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestDashboard:
    def test_dashboard_summary(self, client: TestClient) -> None:
        response = client.get("/api/v1/dashboard", headers=_bearer(client))

        assert response.status_code == 200
        data = response.json()
        assert data["counts"] == {"COMPLETED": 3}
        assert data["recent"] == []

    def test_dashboard_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/dashboard")

        assert response.status_code == 401
