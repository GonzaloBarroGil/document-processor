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
def bdd_mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_documents = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    repo.update_parsed_data = AsyncMock()
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
def bdd_test_client(
    api_key_hash: str,
    bdd_mock_repo: MagicMock,
    bdd_mock_storage: MagicMock,
    bdd_mock_ocr: MagicMock,
) -> TestClient:
    service = DocumentService(
        repository=bdd_mock_repo,
        storage=bdd_mock_storage,
        ocr=bdd_mock_ocr,
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
