from datetime import UTC, datetime
from uuid import uuid4

from pytest_bdd import given, parsers, scenarios, then, when

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)


def _make_docs(count: int, status: DocumentStatus | None = None):
    docs = []
    for i in range(count):
        doc_status = status if status else DocumentStatus.COMPLETED
        docs.append(
            Document(
                id=uuid4(),
                type=DocumentType.INVOICE,
                region="AR",
                status=doc_status,
                media_type=MediaType.JPEG,
                image_key=f"images/{i}.jpg",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    return docs


@given(
    parsers.parse("{count:d} documents exist in the system"),
    target_fixture="bdd_list_setup",
)
def step_docs_exist(bdd_mock_repo, count: int):
    docs = _make_docs(count)

    def _paginated_list(status=None, type=None, region=None, page=1, size=20):
        start = (page - 1) * size
        end = start + size
        return (docs[start:end], len(docs))

    bdd_mock_repo.list_documents.side_effect = _paginated_list
    bdd_mock_repo.list_documents.return_value = None
    return {"docs": docs, "total": count}


@given(
    parsers.parse("{pending:d} PENDING and {completed:d} COMPLETED documents exist"),
    target_fixture="bdd_list_setup",
)
def step_filtered_docs_exist(bdd_mock_repo, pending: int, completed: int):
    pending_docs = _make_docs(pending, DocumentStatus.PENDING)
    completed_docs = _make_docs(completed, DocumentStatus.COMPLETED)

    def _list_side_effect(status=None, type=None, region=None, page=1, size=20):
        if status == DocumentStatus.COMPLETED:
            return (completed_docs, len(completed_docs))
        if status == DocumentStatus.PENDING:
            return (pending_docs, len(pending_docs))
        return (pending_docs + completed_docs, len(pending_docs) + len(completed_docs))

    bdd_mock_repo.list_documents.side_effect = _list_side_effect
    bdd_mock_repo.list_documents.return_value = None
    return {"pending": pending, "completed": completed}


@when(
    parsers.parse("I GET /documents with page {page:d} and size {size:d}"),
    target_fixture="bdd_response",
)
def step_list_paginated(bdd_test_client, page: int, size: int):
    response = bdd_test_client.get(
        "/api/v1/documents",
        params={"page": page, "size": size},
        headers={"X-API-Key": "test-api-key"},
    )
    return {"response": response}


@when(
    parsers.parse('I GET /documents with status "{status}"'),
    target_fixture="bdd_response",
)
def step_list_by_status(bdd_test_client, status: str):
    response = bdd_test_client.get(
        "/api/v1/documents",
        params={"status": status},
        headers={"X-API-Key": "test-api-key"},
    )
    return {"response": response}


@then(parsers.parse("the response status is {status:d}"))
def step_response_status(bdd_response, status: int):
    assert bdd_response["response"].status_code == status


@then(parsers.parse("the body contains {count:d} items"))
def step_body_item_count(bdd_response, count: int):
    data = bdd_response["response"].json()
    assert len(data["items"]) == count


@then(parsers.parse("the body contains total {total:d}"))
def step_body_total(bdd_response, total: int):
    data = bdd_response["response"].json()
    assert data["total"] == total


@then(parsers.parse("the body contains pages {pages:d}"))
def step_body_pages(bdd_response, pages: int):
    data = bdd_response["response"].json()
    assert data["pages"] == pages


@then(parsers.parse('all returned items have status "{status}"'))
def step_all_items_status(bdd_response, status: str):
    data = bdd_response["response"].json()
    for item in data["items"]:
        assert item["status"] == status, f"Expected {status}, got {item['status']}"


scenarios("../features/document_list.feature")
