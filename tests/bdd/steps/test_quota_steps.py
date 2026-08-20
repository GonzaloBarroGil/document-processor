from unittest.mock import AsyncMock

from pytest_bdd import given, scenarios, then, when

from document_processor.core.config import settings


@given("the global daily count is below the cap", target_fixture="bdd_quota_setup")
def step_below_cap() -> dict:
    return {}


@given("the global daily cap has been reached", target_fixture="bdd_quota_setup")
def step_cap_reached(bdd_mock_usage_repo) -> dict:
    bdd_mock_usage_repo.increment = AsyncMock(return_value=settings.daily_document_cap + 1)
    return {}


@when("a client ingests a document", target_fixture="bdd_response")
def step_ingest(bdd_test_client) -> dict:
    response = bdd_test_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "test-api-key"},
        files={"file": ("invoice.jpg", b"data", "image/jpeg")},
        data={"type": "invoice", "region": "AR"},
    )
    return {"response": response}


@then("the response is accepted")
def step_accepted(bdd_response) -> None:
    assert bdd_response["response"].status_code == 202


@then("the response is 429")
def step_429(bdd_response) -> None:
    assert bdd_response["response"].status_code == 429


scenarios("../features/daily_quota.feature")
