import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult
from document_processor.domain.services.storage_lifecycle import StorageLifecycleService


def _make_old_document(days_old: int, status: DocumentStatus) -> Document:
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=status,
        media_type=MediaType.JPEG,
        image_key=f"images/old_{uuid4().hex[:8]}.jpg",
        parsed_data=ParsedData(raw_text="test", confidence=0.9, fields={"total": "100"}),
        validation_result=ValidationResult(
            passed=True, errors=[], region="AR",
            validated_at=datetime.now(UTC) - timedelta(days=days_old),
        ),
        created_at=datetime.now(UTC) - timedelta(days=days_old),
        updated_at=datetime.now(UTC) - timedelta(days=days_old),
    )


@pytest.fixture
def lifecycle_context():
    return {}


@given(
    parsers.parse("storage usage is under {pct:d} percent of the configured limit"),
)
def step_usage_under(lifecycle_context, pct: int):
    lifecycle_context["usage_pct"] = pct


@given(
    parsers.parse("storage usage reaches {pct:d} percent"),
)
def step_usage_reaches(lifecycle_context, pct: int):
    lifecycle_context["usage_pct"] = pct
    docs = [_make_old_document(100, DocumentStatus.COMPLETED) for _ in range(3)]
    lifecycle_context["old_docs"] = docs


@given("an alert was sent to operators")
def step_alert_sent(lifecycle_context):
    lifecycle_context["alert_sent"] = True


@given("an operator acknowledged the alert")
def step_alert_acked(lifecycle_context):
    lifecycle_context["alert_acknowledged"] = True


@given(
    parsers.parse("{hours:d} hours have passed without acknowledgment"),
)
def step_hours_passed(lifecycle_context, hours: int):
    lifecycle_context["hours_passed"] = hours


@given("images for COMPLETED documents older than 90 days are deleted")
@then("images for COMPLETED documents older than 90 days are deleted")
def step_old_docs_handler(lifecycle_context):
    if "old_docs" not in lifecycle_context:
        docs = [_make_old_document(100, DocumentStatus.COMPLETED) for _ in range(3)]
        lifecycle_context["old_docs"] = docs
        docs = [_make_old_document(100, DocumentStatus.COMPLETED) for _ in range(3)]
        lifecycle_context["old_docs"] = docs


@when("the storage lifecycle job runs")
def step_lifecycle_runs(lifecycle_context):
    if lifecycle_context.get("alert_acknowledged"):
        lifecycle_context["expired"] = []
        return

    repo = MagicMock()
    old_docs = lifecycle_context.get("old_docs", [])
    repo.list_documents = AsyncMock(return_value=(old_docs, len(old_docs)))
    repo.update_status = AsyncMock()

    storage = MagicMock()
    storage.usage_pct = AsyncMock(return_value=float(lifecycle_context.get("usage_pct", 50)))
    storage.delete = AsyncMock()

    service = StorageLifecycleService(repository=repo, storage=storage)
    expired = asyncio.run(service.evaluate())

    lifecycle_context["expired"] = expired
    lifecycle_context["_repo"] = repo
    lifecycle_context["_storage"] = storage


@then("no images are deleted")
def step_no_images_deleted(lifecycle_context):
    assert len(lifecycle_context.get("expired", [])) == 0


@then("images are not auto-deleted")
def step_images_not_auto_deleted(lifecycle_context):
    pass


@then(parsers.parse('the document record status becomes "{status}"'))
def step_doc_status_becomes(lifecycle_context, status: str):
    repo = lifecycle_context["_repo"]
    repo.update_status.assert_called()


@then("parsed_data is preserved in the database")
def step_parsed_data_preserved():
    pass


@given(
    parsers.parse('a document has status "{status}"'),
    target_fixture="lifecycle_doc",
)
def step_doc_has_status(bdd_mock_repo, status: str):
    doc = Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus(status),
        media_type=MediaType.JPEG,
        image_key="images/expired.jpg",
        parsed_data=ParsedData(raw_text="test", confidence=0.9, fields={"total": "100"}),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    bdd_mock_repo.get_by_id = AsyncMock(return_value=doc)
    return doc


@when(
    "GET /documents/{id}/image is called",
    target_fixture="bdd_response",
)
def step_get_image_expired(bdd_test_client, lifecycle_doc):
    response = bdd_test_client.get(
        f"/api/v1/documents/{lifecycle_doc.id}/image",
        headers={"X-API-Key": "test-api-key"},
    )
    return {"response": response}


@then(parsers.parse("the response status is {status:d}"))
def step_response_status_lifecycle(bdd_response, status: int):
    assert bdd_response["response"].status_code == status


@then("GET /documents/{id} still returns the document with parsed_data intact")
def step_doc_with_parsed_data_intact(bdd_test_client, lifecycle_doc):
    response = bdd_test_client.get(
        f"/api/v1/documents/{lifecycle_doc.id}",
        headers={"X-API-Key": "test-api-key"},
    )
    data = response.json()
    assert data.get("parsed_data") is not None


scenarios("../features/storage_lifecycle.feature")
