import hashlib
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
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService

_API_KEY = "test-api-key"


def _make_document() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.COMPLETED,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        parsed_data=ParsedData(
            raw_text="Total: 1500",
            confidence=0.95,
            fields={"total": "1500"},
        ),
        created_at=now,
        updated_at=now,
    )


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
    export_service = ExportService(repository=repo)

    api_key_hash = hashlib.sha256(_API_KEY.encode()).hexdigest()
    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(side_effect=lambda h: h == api_key_hash)

    app = create_app(
        document_service=document_service,
        api_key_repository=api_key_repo,
        validator_registry={},
        export_service=export_service,
    )
    return TestClient(app)


class TestExport:
    def test_export_json(self, client: TestClient) -> None:
        from document_processor.adapters.web.api.deps import get_export_service

        doc = _make_document()
        get_export_service()._repository.get_by_id = AsyncMock(return_value=doc)

        response = client.get(f"/api/v1/documents/{doc.id}/export", headers={"X-API-Key": _API_KEY})

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(doc.id)
        assert data["status"] == "COMPLETED"

    def test_export_csv(self, client: TestClient) -> None:
        from document_processor.adapters.web.api.deps import get_export_service

        doc = _make_document()
        get_export_service()._repository.get_by_id = AsyncMock(return_value=doc)

        response = client.get(
            f"/api/v1/documents/{doc.id}/export",
            headers={"X-API-Key": _API_KEY, "Accept": "text/csv"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "total,1500" in response.text

    def test_export_not_found(self, client: TestClient) -> None:
        response = client.get(
            f"/api/v1/documents/{uuid4()}/export", headers={"X-API-Key": _API_KEY}
        )

        assert response.status_code == 404

    def test_export_requires_auth(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/documents/{uuid4()}/export")

        assert response.status_code == 401
