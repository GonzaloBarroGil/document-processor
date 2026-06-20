import asyncio

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from document_processor.adapters.validators.ar.validator import ArgentinaValidator


@pytest.fixture
def ar_validator_fields() -> dict[str, str]:
    return {}


@pytest.fixture
def ar_validator() -> ArgentinaValidator:
    return ArgentinaValidator()


@given(parsers.parse('parsed data contains tipo_comprobante "{tipo}" and cuit_emisor "{cuit}"'))
def step_afip_data(ar_validator_fields, tipo: str, cuit: str) -> None:
    ar_validator_fields["tipo_comprobante"] = tipo
    ar_validator_fields["cuit_emisor"] = cuit
    ar_validator_fields["cae"] = "12345678901234"


@given("the CAE number is present and properly formatted")
def step_cae_ok() -> None:
    pass


@given(parsers.parse('parsed data contains cuit_emisor "{cuit}"'))
def step_cuit_data(ar_validator_fields, cuit: str) -> None:
    ar_validator_fields["cuit_emisor"] = cuit


@given(parsers.parse('parsed data is missing "{field}" for an invoice type that requires it'))
def step_missing_field(ar_validator_fields, field: str) -> None:
    ar_validator_fields["tipo_comprobante"] = "A"
    ar_validator_fields.pop(field, None)


@when("the Argentina validator runs", target_fixture="bdd_response")
def step_run_validator(ar_validator: ArgentinaValidator, ar_validator_fields: dict[str, str]):
    result = asyncio.run(ar_validator.validate(ar_validator_fields))
    return {"validation": result}


@then(parsers.parse('validation_result is "{expected}"'))
def step_validation_result(bdd_response, expected: str):
    if expected == "PASS":
        assert bdd_response["validation"].passed is True
    else:
        assert bdd_response["validation"].passed is False


@then(parsers.parse('errors include field "{field}" with rule "{rule}"'))
def step_validation_error(bdd_response, field: str, rule: str):
    errors = bdd_response["validation"].errors
    assert any(
        e.field == field and e.rule == rule for e in errors
    ), f"No error with field={field} rule={rule} in {errors}"


scenarios("../features/regional_validation_ar.feature")
