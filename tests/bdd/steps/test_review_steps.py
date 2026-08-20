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


def _make_document() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.VALIDATION_FAILED,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        created_at=now,
        updated_at=now,
    )


def _bearer(bdd_test_client) -> dict:
    response = bdd_test_client.post(
        "/api/v1/auth/login",
        json={"username": "reviewer", "password": "s3cret"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@given("a document is in the review queue", target_fixture="bdd_review_setup")
def step_review_doc(bdd_mock_repo) -> dict:
    doc = _make_document()
    bdd_mock_repo.get_by_id = AsyncMock(side_effect=[doc, doc])
    return {"document_id": doc.id}


@when("the reviewer edits parsed fields and approves", target_fixture="bdd_response")
def step_approve(bdd_test_client, bdd_review_setup) -> dict:
    response = bdd_test_client.patch(
        f"/api/v1/documents/{bdd_review_setup['document_id']}/review",
        headers=_bearer(bdd_test_client),
        json={"action": "approve", "edited_fields": {"total": "1500"}},
    )
    return {"response": response}


@when("the reviewer requests changes with a comment", target_fixture="bdd_response")
def step_request_changes(bdd_test_client, bdd_review_setup) -> dict:
    response = bdd_test_client.patch(
        f"/api/v1/documents/{bdd_review_setup['document_id']}/review",
        headers=_bearer(bdd_test_client),
        json={"action": "request_changes", "comment": "Please recheck"},
    )
    return {"response": response}


@then("the document is marked reviewed")
def step_marked_reviewed(bdd_response, bdd_mock_repo) -> None:
    assert bdd_response["response"].status_code == 200
    assert bdd_mock_repo.update_review.call_args.kwargs["reviewed"] is True


@then("the document is flagged for re-extraction")
def step_flagged(bdd_response, bdd_mock_repo) -> None:
    assert bdd_response["response"].status_code == 200
    assert bdd_mock_repo.update_review.call_args.kwargs["reviewed"] is False
    assert bdd_mock_repo.update_review.call_args.kwargs["status"] == DocumentStatus.PENDING


scenarios("../features/manual_review.feature")
