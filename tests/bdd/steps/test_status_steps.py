from datetime import UTC, datetime
from uuid import UUID, uuid4

from pytest_bdd import given, parsers, scenarios, then, when

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult

_ID_MAP = {
    "doc-123": UUID("11111111-1111-1111-1111-111111111111"),
    "doc-456": UUID("22222222-2222-2222-2222-222222222222"),
    "unknown-id": UUID("00000000-0000-0000-0000-000000000000"),
}


def _make_doc(status: DocumentStatus, parsed_data=None, validation_result=None):
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=status,
        media_type=MediaType.JPEG,
        image_key="images/test.jpg",
        parsed_data=parsed_data,
        validation_result=validation_result,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@given(
    parsers.parse('a document with id "{doc_id}" exists and status is "{status}"'),
    target_fixture="bdd_mock_doc",
)
def step_doc_exists(bdd_mock_repo, doc_id: str, status: str):
    parsed = ParsedData(raw_text="test", confidence=0.9, fields={"total": "100"})
    result = ValidationResult(passed=True, errors=[], region="AR", validated_at=datetime.now(UTC))
    doc = _make_doc(DocumentStatus(status), parsed_data=parsed, validation_result=result)
    real_id = _ID_MAP.get(doc_id, UUID(doc_id) if _is_uuid(doc_id) else uuid4())
    bdd_mock_repo.get_by_id.return_value = doc
    bdd_mock_repo.get_by_id.side_effect = None
    return {"doc": doc, "real_id": real_id}


@given(
    parsers.parse('no document with id "{doc_id}" exists'),
    target_fixture="bdd_mock_doc",
)
def step_no_doc_exists(bdd_mock_repo, doc_id: str):
    bdd_mock_repo.get_by_id.return_value = None
    bdd_mock_repo.get_by_id.side_effect = None
    real_id = _ID_MAP.get(doc_id, uuid4())
    return {"real_id": real_id}


@given(
    parsers.parse('a document with id "{doc_id}" has status "{status}"'),
    target_fixture="bdd_mock_doc",
)
def step_doc_has_status(bdd_mock_repo, doc_id: str, status: str):
    doc = _make_doc(DocumentStatus(status))
    real_id = _ID_MAP.get(doc_id, uuid4())
    bdd_mock_repo.get_by_id.return_value = doc
    bdd_mock_repo.get_by_id.side_effect = None
    return {"doc": doc, "real_id": real_id}


@when(
    parsers.parse("I GET /documents/{doc_id}"),
    target_fixture="bdd_response",
)
def step_get_document(bdd_test_client, bdd_mock_doc, doc_id: str):
    real_id = bdd_mock_doc.get("real_id", doc_id)
    response = bdd_test_client.get(
        f"/api/v1/documents/{real_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    return {"response": response}


@then(parsers.parse("the response status is {status:d}"))
def step_response_status(bdd_response, status: int):
    assert bdd_response["response"].status_code == status


@then(parsers.parse('the body contains status "{status}"'))
def step_body_contains_status(bdd_response, status: str):
    data = bdd_response["response"].json()
    assert data.get("status") == status


@then("the body includes parsed_data with extracted fields")
def step_body_includes_parsed_data(bdd_response):
    data = bdd_response["response"].json()
    assert data.get("parsed_data") is not None
    assert data["parsed_data"].get("fields") is not None


@then("the body includes validation_result with pass/fail")
def step_body_includes_validation_result(bdd_response):
    data = bdd_response["response"].json()
    assert data.get("validation_result") is not None
    assert "passed" in data["validation_result"]


@then("parsed_data is null")
def step_parsed_data_null(bdd_response):
    data = bdd_response["response"].json()
    assert data.get("parsed_data") is None


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


scenarios("../features/document_status.feature")
