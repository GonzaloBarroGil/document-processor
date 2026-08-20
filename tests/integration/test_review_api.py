from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.review_service import ReviewService
from document_processor.domain.services.token_service import TokenService


def _make_doc() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.VALIDATION_FAILED,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        created_at=now,
        updated_at=now,
    )


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
    repo.update_review = AsyncMock()
    repo.list_review_queue = AsyncMock(return_value=([], 0))

    storage = MagicMock()
    storage.store = AsyncMock()
    storage.retrieve = AsyncMock()

    document_service = DocumentService(
        repository=repo,
        storage=storage,
        ocr=MagicMock(),
        validator_registry={},
    )
    review_service = ReviewService(repository=repo)

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
        review_service=review_service,
    )
    return TestClient(app)


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "alice", "password": "s3cret"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestReviewEndpoints:
    def test_review_requires_auth(self, client: TestClient) -> None:
        response = client.patch(f"/api/v1/documents/{uuid4()}/review", json={"action": "approve"})
        assert response.status_code == 401

    def test_review_approve_success(self, client: TestClient) -> None:
        from document_processor.adapters.web.api.deps import get_review_service

        doc = _make_doc()
        get_review_service()._repository.get_by_id = AsyncMock(side_effect=[doc, doc])

        response = client.patch(
            f"/api/v1/documents/{doc.id}/review",
            headers=_auth_headers(client),
            json={"action": "approve", "edited_fields": {"total": "1500"}},
        )

        assert response.status_code == 200

    def test_review_not_found(self, client: TestClient) -> None:
        from document_processor.adapters.web.api.deps import get_review_service

        get_review_service()._repository.get_by_id = AsyncMock(return_value=None)

        response = client.patch(
            f"/api/v1/documents/{uuid4()}/review",
            headers=_auth_headers(client),
            json={"action": "approve"},
        )

        assert response.status_code == 404

    def test_review_queue_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/review/queue")
        assert response.status_code == 401

    def test_review_queue_success(self, client: TestClient) -> None:
        response = client.get("/api/v1/review/queue", headers=_auth_headers(client))

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
