import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.domain.services.document_service import DocumentService


@pytest.fixture
def api_key_hash() -> str:
    return hashlib.sha256(b"test-api-key").hexdigest()


@pytest.fixture
def bdd_test_client(api_key_hash: str) -> TestClient:
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

    service = DocumentService(
        repository=repo,
        storage=storage,
        ocr=ocr,
        validator_registry={},
    )

    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(
        side_effect=lambda h: h == api_key_hash
    )

    app = create_app(
        document_service=service,
        api_key_repository=api_key_repo,
        validator_registry={},
    )
    return TestClient(app)


@pytest.fixture
def bdd_payload() -> tuple:
    return ("unknown.jpg", b"", "image/jpeg", "invoice", "AR")


@pytest.fixture
def bdd_response() -> dict:
    return {}
