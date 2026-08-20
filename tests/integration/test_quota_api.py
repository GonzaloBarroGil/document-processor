import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.core.config import settings
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.quota_service import QuotaService

_API_KEY = "test-api-key"


@pytest.fixture
def client() -> TestClient:
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

    usage = MagicMock()
    usage.increment = AsyncMock(return_value=1)
    usage.get = AsyncMock(return_value=0)
    quota_service = QuotaService(usage_repository=usage)

    api_key_hash = hashlib.sha256(_API_KEY.encode()).hexdigest()
    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(side_effect=lambda h: h == api_key_hash)

    app = create_app(
        document_service=document_service,
        api_key_repository=api_key_repo,
        validator_registry={},
        quota_service=quota_service,
    )
    return TestClient(app)


def _ingest(client: TestClient) -> None:
    return client.post(
        "/api/v1/documents",
        headers={"X-API-Key": _API_KEY},
        files={"file": ("invoice.jpg", b"data", "image/jpeg")},
        data={"type": "invoice", "region": "AR"},
    )


class TestQuota:
    def test_within_quota_accepted(self, client: TestClient) -> None:
        response = _ingest(client)

        assert response.status_code == 202

    def test_over_quota_rejected(self, client: TestClient) -> None:
        from document_processor.adapters.web.api.deps import get_quota_service

        get_quota_service()._usage_repository.increment = AsyncMock(
            return_value=settings.daily_document_cap + 1
        )

        response = _ingest(client)

        assert response.status_code == 429
        assert "Retry-After" in response.headers
