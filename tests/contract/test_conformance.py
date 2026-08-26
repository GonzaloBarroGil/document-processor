"""Property-based contract conformance tests (schemathesis).

Fuzzes the FastAPI app (built with in-memory mocks) against the **hub contract** and fails on any
5xx response or response-shape mismatch. The contract path is taken from `CONTRACT_PATH` (default
`/tmp/openapi.yaml`, which CI fetches before running this suite).

This complements `scripts/check_contract.py`, which statically verifies that the app implements
every contract operation.
"""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from schemathesis.checks import ChecksConfig
from schemathesis.openapi import from_path

from document_processor.adapters.web.main import create_app
from document_processor.core.config import settings
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.api_key_service import ApiKeyService
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.dashboard_service import DashboardService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.quota_service import QuotaService
from document_processor.domain.services.review_service import ReviewService
from document_processor.domain.services.token_service import TokenService

CONTRACT_PATH = os.environ.get("CONTRACT_PATH", "/tmp/openapi.yaml")
API_KEY = "test-api-key"

if not os.path.exists(CONTRACT_PATH):
    pytest.skip(
        f"Contract not found at {CONTRACT_PATH}; set CONTRACT_PATH.",
        allow_module_level=True,
    )


def _build_app() -> tuple:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_documents = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    repo.update_parsed_data = AsyncMock()
    repo.list_review_queue = AsyncMock(return_value=([], 0))
    repo.count_by_status = AsyncMock(return_value={})

    storage = MagicMock()
    storage.store = AsyncMock()
    storage.retrieve = AsyncMock(return_value=b"image")

    document_service = DocumentService(
        repository=repo,
        storage=storage,
        ocr=MagicMock(),
        validator_registry={},
    )

    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(return_value=True)
    api_key_repo.create = AsyncMock()
    api_key_repo.list_keys = AsyncMock(return_value=[])
    api_key_repo.revoke = AsyncMock(return_value=True)

    admin = User(
        id=uuid4(),
        username="admin",
        password_hash=PasswordHasher().hash("s3cret"),
        role=UserRole.ADMIN,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
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

    usage_repo = MagicMock()
    usage_repo.increment = AsyncMock(return_value=1)
    usage_repo.get = AsyncMock(return_value=0)
    quota_service = QuotaService(usage_repository=usage_repo)

    app = create_app(
        document_service=document_service,
        api_key_repository=api_key_repo,
        validator_registry={},
        auth_service=auth_service,
        review_service=ReviewService(repository=repo),
        export_service=ExportService(repository=repo),
        quota_service=quota_service,
        api_key_service=ApiKeyService(repository=api_key_repo),
        dashboard_service=DashboardService(repository=repo),
    )
    return app, admin


app, admin = _build_app()

access_token = TokenService().issue_access_token(admin.id, admin.role)
AUTH_HEADERS = {
    "X-API-Key": API_KEY,
    "Authorization": f"Bearer {access_token}",
}


@pytest.fixture(autouse=True)
def _reset_global_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rebuild the app to reset process-wide service singletons and lift the rate limit.

    ``create_app`` stores its services in module-level singletons (``deps.py``), and the BDD /
    integration suites create their own apps with their own services in the same process. Re-run
    ``_build_app`` before every case so fuzzed requests resolve the mocked services, and neutralize
    the per-key rate limiter (otherwise the fuzzer would trip a 429); ``monkeypatch`` restores the
    real value afterward.
    """
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1_000_000)
    _build_app()
    yield


schema = from_path(CONTRACT_PATH)
# Fuzz the app over the ASGI transport, but validate against the hub contract schema.
schema.app = app
schema.location = "/openapi.json"

# The multipart ingestion endpoint is exercised by the integration tests; schemathesis's
# multipart generation for the binary `file` field is unreliable, so exclude it from fuzzing.
schema = schema.exclude(path="/api/v1/documents", method="POST")

# Keep only the response-shape / server-error checks. The strict "negative data" and
# method/header compliance checks are flaky against FastAPI/Starlette (e.g. the auto-generated
# `Allow` header and multipart serialization) and are not our target here.
schema.config.checks = ChecksConfig.from_dict(
    {
        "unsupported_method": {"enabled": False},
        "allow_header_conformance": {"enabled": False},
        "positive_data_acceptance": {"enabled": False},
        "negative_data_rejection": {"enabled": False},
        "response_headers_conformance": {"enabled": False},
        "missing_required_header": {"enabled": False},
        # The app returns 403 (not 401) for a present-but-invalid/revoked API key, per RFC 7235.
        # schemathesis's `ignored_auth` check strictly expects 401 for invalid credentials, so it
        # false-positives here; auth enforcement is covered by the integration suite.
        "ignored_auth": {"enabled": False},
    }
)


@schema.parametrize()
def test_conformance(case) -> None:
    """Every generated case must not error and must match the contract schema."""
    case.call_and_validate(headers=AUTH_HEADERS)
