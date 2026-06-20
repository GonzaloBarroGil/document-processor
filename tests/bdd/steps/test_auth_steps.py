from pytest_bdd import given, scenarios, then, when
from starlette.testclient import TestClient


@given(
    "client provides header X-API-Key with a valid key", target_fixture="bdd_response"
)
def step_valid_key_request(bdd_test_client):
    response = bdd_test_client.get(
        "/api/v1/health",
        headers={"X-API-Key": "test-api-key"},
    )
    return {"response": response}


@given("client does not provide the X-API-Key header", target_fixture="bdd_response")
def step_no_key_request(bdd_test_client):
    response = bdd_test_client.get("/api/v1/documents")
    return {"response": response}


@given(
    "client provides an invalid or revoked API key", target_fixture="bdd_response"
)
def step_invalid_key_request(bdd_test_client):
    response = bdd_test_client.get(
        "/api/v1/documents",
        headers={"X-API-Key": "invalid-key"},
    )
    return {"response": response}


@given("any client", target_fixture="bdd_response")
def step_any_client_health(bdd_test_client):
    response = bdd_test_client.get("/api/v1/health")
    return {"response": response}


@when("client makes any request")
def step_client_makes_request(bdd_response):
    pass


@when("GET /health is called without an API key")
def step_health_no_key(bdd_response):
    pass


@then("the request is processed normally")
def step_request_ok(bdd_response):
    assert bdd_response["response"].status_code in (200, 202)


@then("the response status is 200")
def step_status_200(bdd_response):
    assert bdd_response["response"].status_code == 200


@then("the response status is 401")
def step_status_401(bdd_response):
    assert bdd_response["response"].status_code == 401


@then("the response status is 403")
def step_status_403(bdd_response):
    assert bdd_response["response"].status_code == 403


scenarios("../features/authentication.feature")
