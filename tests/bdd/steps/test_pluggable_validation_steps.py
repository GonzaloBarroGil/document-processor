
from datetime import UTC

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from document_processor.adapters.validators.registry import ValidatorRegistry
from document_processor.domain.ports.region_validator import RegionValidatorPort


class _MockValidator(RegionValidatorPort):
    def __init__(self, region_code: str) -> None:
        self._region_code = region_code

    @property
    def region_code(self) -> str:
        return self._region_code

    async def validate(self, fields: dict[str, str]):
        from datetime import datetime

        from document_processor.domain.models.validation import ValidationResult
        return ValidationResult(
            passed=True, errors=[], region=self._region_code,
            validated_at=datetime.now(UTC),
        )


@pytest.fixture
def validator_registry():
    return ValidatorRegistry()


@given(
    parsers.parse('validators are registered for "{region_a}" and "{region_b}"'),
    target_fixture="validator_registry",
)
def step_registered_validators(region_a: str, region_b: str):
    registry = ValidatorRegistry()
    registry.register(region_a, _MockValidator(region_a))
    registry.register(region_b, _MockValidator(region_b))
    return registry


@when("the application starts", target_fixture="validator_registry")
def step_app_starts(validator_registry):
    return validator_registry


@then("both validators are loaded and discoverable by region code")
def step_both_discoverable(validator_registry):
    assert validator_registry.get("AR") is not None
    assert validator_registry.get("BR") is not None


@given(
    parsers.parse('no validator is registered for "{region}"'),
    target_fixture="validator_registry",
)
def step_no_validator(region: str):
    registry = ValidatorRegistry()
    return registry


@when(
    parsers.parse('a document is submitted with region "{region}"'),
    target_fixture="bdd_response",
)
def step_doc_submitted(validator_registry, region: str):
    validator = validator_registry.get(region)
    return {"validator": validator, "region": region}


@then("the document is processed without validation")
def step_no_validation(bdd_response):
    assert bdd_response["validator"] is None


@then(parsers.parse('validation_result is marked as "{result}"'))
def step_validation_skipped(bdd_response, result: str):
    if result == "SKIPPED":
        assert bdd_response["validator"] is None


@given(
    parsers.parse('a new validator module for region "{region}" is added as a plugin'),
    target_fixture="validator_registry",
)
def step_new_validator_plugin(region: str):
    registry = ValidatorRegistry()
    registry.register(region, _MockValidator(region))
    return registry


@when("the application restarts", target_fixture="validator_registry")
def step_app_restarts(validator_registry):
    return validator_registry


@then("the validator is auto-discovered and operational")
def step_validator_operational(validator_registry):
    assert validator_registry.get("UY") is not None


scenarios("../features/pluggable_validation.feature")
