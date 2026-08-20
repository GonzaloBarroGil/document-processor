from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from pytest_bdd import given, scenarios, then, when

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData


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
            raw_text="total: 100",
            confidence=0.95,
            fields={"total": "100"},
        ),
        created_at=now,
        updated_at=now,
    )


@given("a COMPLETED document", target_fixture="bdd_export_setup")
def step_completed_doc(bdd_mock_repo) -> dict:
    doc = _make_document()
    bdd_mock_repo.get_by_id = AsyncMock(return_value=doc)
    return {"document_id": doc.id}


@when("the operator requests export", target_fixture="bdd_response")
def step_export_json(bdd_test_client, bdd_export_setup) -> dict:
    response = bdd_test_client.get(
        f"/api/v1/documents/{bdd_export_setup['document_id']}/export",
        headers={"X-API-Key": "test-api-key"},
    )
    return {"response": response}


@when("the operator requests export with Accept: text/csv", target_fixture="bdd_response")
def step_export_csv(bdd_test_client, bdd_export_setup) -> dict:
    response = bdd_test_client.get(
        f"/api/v1/documents/{bdd_export_setup['document_id']}/export",
        headers={"X-API-Key": "test-api-key", "Accept": "text/csv"},
    )
    return {"response": response}


@then("a flattened JSON payload is returned")
def step_json_payload(bdd_response) -> None:
    assert bdd_response["response"].status_code == 200
    data = bdd_response["response"].json()
    assert data["document_id"]
    assert data["status"] == "COMPLETED"


@then("a CSV payload is returned")
def step_csv_payload(bdd_response) -> None:
    assert bdd_response["response"].status_code == 200
    assert "text/csv" in bdd_response["response"].headers["content-type"]
    assert "total,100" in bdd_response["response"].text


scenarios("../features/export.feature")
