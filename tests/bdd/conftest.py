import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.quota_service import QuotaService
from document_processor.domain.services.review_service import ReviewService
from document_processor.domain.services.token_service import TokenService

_REVIEWER_PASSWORD_HASH = PasswordHasher().hash("s3cret")


@pytest.fixture
def api_key_hash() -> str:
    return hashlib.sha256(b"test-api-key").hexdigest()


@pytest.fixture
def bdd_mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_documents = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    repo.update_parsed_data = AsyncMock()
    repo.update_review = AsyncMock()
    repo.list_review_queue = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def bdd_mock_storage() -> MagicMock:
    storage = MagicMock()
    storage.store = AsyncMock()
    storage.retrieve = AsyncMock()
    return storage


@pytest.fixture
def bdd_mock_ocr() -> MagicMock:
    return MagicMock()


@pytest.fixture
def bdd_mock_usage_repo() -> MagicMock:
    usage = MagicMock()
    usage.increment = AsyncMock(return_value=1)
    usage.get = AsyncMock(return_value=0)
    return usage


@pytest.fixture
def bdd_user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="reviewer",
        password_hash=_REVIEWER_PASSWORD_HASH,
        role=UserRole.REVIEWER,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def bdd_test_client(
    api_key_hash: str,
    bdd_mock_repo: MagicMock,
    bdd_mock_storage: MagicMock,
    bdd_mock_ocr: MagicMock,
    bdd_mock_usage_repo: MagicMock,
    bdd_user: User,
) -> TestClient:
    document_service = DocumentService(
        repository=bdd_mock_repo,
        storage=bdd_mock_storage,
        ocr=bdd_mock_ocr,
        validator_registry={},
    )

    user_repo = MagicMock()
    user_repo.get_user_by_username = AsyncMock(return_value=bdd_user)
    user_repo.get_user_by_id = AsyncMock(return_value=bdd_user)
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

    review_service = ReviewService(repository=bdd_mock_repo)
    export_service = ExportService(repository=bdd_mock_repo)
    quota_service = QuotaService(usage_repository=bdd_mock_usage_repo)

    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(side_effect=lambda h: h == api_key_hash)

    app = create_app(
        document_service=document_service,
        api_key_repository=api_key_repo,
        validator_registry={},
        auth_service=auth_service,
        review_service=review_service,
        export_service=export_service,
        quota_service=quota_service,
    )
    return TestClient(app)


@pytest.fixture
def bdd_payload() -> tuple:
    return ("unknown.jpg", b"", "image/jpeg", "invoice", "AR")


@pytest.fixture
def bdd_response() -> dict:
    return {}
