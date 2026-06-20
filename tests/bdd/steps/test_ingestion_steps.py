from pytest_bdd import given, parsers, scenarios, then, when
from starlette.testclient import TestClient


def _do_post(
    client: TestClient,
    filename: str,
    data: bytes,
    content_type: str,
    doc_type: str = "invoice",
    region: str = "AR",
):
    return client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "test-api-key"},
        files={"file": (filename, data, content_type)},
        data={"type": doc_type, "region": region},
    )


@given("a valid JPEG image of an invoice under 10MB", target_fixture="bdd_payload")
def step_jpeg():
    return ("invoice.jpg", b"fake-jpeg-data", "image/jpeg", "invoice", "AR")


@given("a valid HEIC image of a ticket under 10MB", target_fixture="bdd_payload")
def step_heic():
    return ("ticket.heic", b"fake-heic-data", "image/heic", "ticket", "AR")


@given("a valid PDF document under 10MB", target_fixture="bdd_payload")
def step_pdf():
    return ("invoice.pdf", b"fake-pdf", "application/pdf", "invoice", "AR")


@given('a file of type "application/x-tar"', target_fixture="bdd_payload")
def step_tar():
    return ("file.tar", b"data", "application/x-tar", "invoice", "AR")


@given("a JPEG image of 15MB", target_fixture="bdd_payload")
def step_oversize():
    return ("big.jpg", b"x" * (15 * 1024 * 1024), "image/jpeg", "invoice", "AR")


@when(
    parsers.parse(
        'I POST to /documents with the image, type "{type}", and region "{region}"'
    ),
    target_fixture="bdd_response",
)
def step_post_with_type(bdd_test_client, bdd_payload, type: str, region: str):
    filename, data, content_type, _, _ = bdd_payload
    response = _do_post(bdd_test_client, filename, data, content_type, type, region)
    return {"response": response}


@when("I POST to /documents", target_fixture="bdd_response")
def step_post_simple(bdd_test_client, bdd_payload):
    filename, data, content_type, doc_type, region = bdd_payload
    response = _do_post(bdd_test_client, filename, data, content_type, doc_type, region)
    return {"response": response}


@when(
    'I POST to /documents with type "invoice"', target_fixture="bdd_response"
)
def step_post_type_invoice(bdd_test_client, bdd_payload):
    filename, data, content_type, _, region = bdd_payload
    response = _do_post(bdd_test_client, filename, data, content_type, "invoice", region)
    return {"response": response}


@then(parsers.parse("the response status is {status:d}"))
def step_response_status(bdd_response, status: int):
    assert bdd_response["response"].status_code == status


@then("the response contains a document_id")
def step_contains_document_id(bdd_response):
    data = bdd_response["response"].json()
    assert "document_id" in data


@then('the status is "PENDING"')
def step_status_pending(bdd_response):
    data = bdd_response["response"].json()
    assert data.get("status") == "PENDING"


@then(parsers.parse('the body contains "{text}"'))
def step_body_contains(bdd_response, text: str):
    response_text = bdd_response["response"].text
    assert text in response_text, f"Expected '{text}' in '{response_text}'"


@then("the system will rasterize it for OCR")
def step_rasterize_ocr(bdd_response):
    assert bdd_response["response"].status_code == 202


scenarios("../features/document_ingestion.feature")
