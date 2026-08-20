from pytest_bdd import given, parsers, scenarios, then, when


@given("a user with role REVIEWER exists", target_fixture="bdd_auth_setup")
def step_user_exists() -> dict:
    return {"username": "reviewer", "password": "s3cret"}


@given("a user enters an incorrect password", target_fixture="bdd_auth_setup")
def step_wrong_password() -> dict:
    return {"username": "reviewer", "password": "wrong"}


@when("they log in with valid credentials", target_fixture="bdd_response")
def step_login_valid(bdd_test_client) -> dict:
    response = bdd_test_client.post(
        "/api/v1/auth/login",
        json={"username": "reviewer", "password": "s3cret"},
    )
    return {"response": response}


@when("they attempt to log in", target_fixture="bdd_response")
def step_login_attempt(bdd_test_client, bdd_auth_setup) -> dict:
    response = bdd_test_client.post(
        "/api/v1/auth/login",
        json=bdd_auth_setup,
    )
    return {"response": response}


@given("a user has a valid refresh token", target_fixture="bdd_auth_setup")
def step_valid_refresh_token(bdd_test_client) -> dict:
    response = bdd_test_client.post(
        "/api/v1/auth/login",
        json={"username": "reviewer", "password": "s3cret"},
    )
    return {"refresh_token": response.json()["refresh_token"]}


@when("they exchange the refresh token for a new pair", target_fixture="bdd_response")
def step_exchange_refresh(bdd_test_client, bdd_auth_setup) -> dict:
    response = bdd_test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": bdd_auth_setup["refresh_token"]},
    )
    return {
        "response": response,
        "old_refresh_token": bdd_auth_setup["refresh_token"],
    }


@then("they receive an access token and a refresh token")
def step_receive_tokens(bdd_response) -> None:
    data = bdd_response["response"].json()
    assert data["access_token"]
    assert data["refresh_token"]


@then(parsers.parse("the login response status is {status:d}"))
def step_login_status(bdd_response, status: int) -> None:
    assert bdd_response["response"].status_code == status


@then("they receive a new access token")
def step_receive_new_token(bdd_response) -> None:
    data = bdd_response["response"].json()
    assert data["access_token"]
    assert data["refresh_token"] != bdd_response["old_refresh_token"]


scenarios("../features/jwt_authentication.feature")
