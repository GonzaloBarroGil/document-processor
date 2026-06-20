from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult


def _make_doc(
    doc_id: UUID | None = None,
    status: DocumentStatus = DocumentStatus.COMPLETED,
) -> Document:
    return Document(
        id=doc_id or uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=status,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        parsed_data=(
            ParsedData(raw_text="Total: 100", confidence=0.95, fields={"total": "100"})
            if status == DocumentStatus.COMPLETED
            else None
        ),
        validation_result=(
            ValidationResult(
                passed=True, errors=[], region="AR",
                validated_at=datetime.now(UTC),
            )
            if status == DocumentStatus.COMPLETED
            else None
        ),
        error_detail=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def api_key_hash() -> str:
    import hashlib
    return hashlib.sha256(b"test-api-key").hexdigest()


@pytest.fixture
def client(api_key_hash: str) -> TestClient:
    from document_processor.adapters.web.main import create_app
    from document_processor.domain.services.document_service import DocumentService

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_documents = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    repo.update_parsed_data = AsyncMock()
    storage = MagicMock()
    storage.store = AsyncMock()
    storage.retrieve = AsyncMock()
    ocr = MagicMock()
    validator_registry: dict = {}

    service = DocumentService(
        repository=repo,
        storage=storage,
        ocr=ocr,
        validator_registry=validator_registry,
    )

    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(return_value=False)

    async def validate_key(hash: str) -> bool:
        return hash == api_key_hash

    api_key_repo.validate_key = AsyncMock(side_effect=validate_key)

    app = create_app(
        document_service=service,
        api_key_repository=api_key_repo,
        validator_registry=validator_registry,
    )
    return TestClient(app)


class TestHealth:
    def test_health_no_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestDocumentIngestion:
    def test_post_without_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("invoice.jpg", b"fake-jpeg", "image/jpeg")},
            data={"type": "invoice", "region": "AR"},
        )
        assert response.status_code == 401

    def test_post_with_invalid_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/documents",
            headers={"X-API-Key": "invalid-key"},
            files={"file": ("invoice.jpg", b"fake-jpeg", "image/jpeg")},
            data={"type": "invoice", "region": "AR"},
        )
        assert response.status_code == 403

    def test_post_invalid_media_type(self, client: TestClient, api_key_hash: str) -> None:
        response = client.post(
            "/api/v1/documents",
            headers={"X-API-Key": "test-api-key"},
            files={"file": ("file.tar", b"data", "application/x-tar")},
            data={"type": "invoice", "region": "AR"},
        )
        assert response.status_code in (422, 415)

    def test_post_success(self, client: TestClient, api_key_hash: str) -> None:
        response = client.post(
            "/api/v1/documents",
            headers={"X-API-Key": "test-api-key"},
            files={"file": ("invoice.jpg", b"valid-jpeg-data", "image/jpeg")},
            data={"type": "invoice", "region": "AR"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "PENDING"


class TestDocumentStatus:
    def test_get_document_found(self, client: TestClient, api_key_hash: str) -> None:
        doc = _make_doc()
        from document_processor.adapters.web.api.deps import get_document_service

        service = get_document_service()
        service._repository.get_by_id = AsyncMock(return_value=doc)

        response = client.get(
            f"/api/v1/documents/{doc.id}",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["parsed_data"] is not None

    def test_get_image_success(self, client: TestClient, api_key_hash: str) -> None:
        doc = _make_doc()
        from document_processor.adapters.web.api.deps import get_document_service

        service = get_document_service()
        service._repository.get_by_id = AsyncMock(return_value=doc)
        service._storage.retrieve = AsyncMock(return_value=b"image-bytes")

        response = client.get(
            f"/api/v1/documents/{doc.id}/image",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        assert response.content == b"image-bytes"

    def test_get_image_expired(self, client: TestClient, api_key_hash: str) -> None:
        doc = _make_doc(status=DocumentStatus.IMAGE_EXPIRED)
        from document_processor.adapters.web.api.deps import get_document_service

        service = get_document_service()
        service._repository.get_by_id = AsyncMock(return_value=doc)

        response = client.get(
            f"/api/v1/documents/{doc.id}/image",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 410
    def test_get_not_found(self, client: TestClient, api_key_hash: str) -> None:
        response = client.get(
            f"/api/v1/documents/{uuid4()}",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 404

    def test_list_no_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/documents")
        assert response.status_code == 401

    def test_list_with_data(self, client: TestClient, api_key_hash: str) -> None:
        from document_processor.adapters.web.api.deps import get_document_service

        docs = [_make_doc(doc_id=uuid4()) for _ in range(5)]
        service = get_document_service()
        service._repository.list_documents = AsyncMock(return_value=(docs, 5))

        response = client.get(
            "/api/v1/documents?page=1&size=10",
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pages"] == 1


class TestRateLimit:
    def test_rate_limit_triggers_429(self, client: TestClient, api_key_hash: str) -> None:
        from document_processor.core.config import settings

        original = settings.rate_limit_per_minute
        settings.rate_limit_per_minute = 2

        for _ in range(3):
            response = client.post(
                "/api/v1/documents",
                headers={"X-API-Key": "test-api-key"},
                files={"file": ("invoice.jpg", b"data", "image/jpeg")},
                data={"type": "invoice", "region": "AR"},
            )

        settings.rate_limit_per_minute = original

        assert response.status_code == 429
        assert "Retry-After" in response.headers
