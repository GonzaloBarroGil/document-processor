from datetime import UTC, datetime

from document_processor.domain.models.validation import (
    ValidationResult,
)
from document_processor.domain.ports.region_validator import RegionValidatorPort


class ValidateOutput:
    """The validation result produced by the validate step."""

    def __init__(self, validation_result: ValidationResult) -> None:
        self.validation_result = validation_result


async def validate(
    validator: RegionValidatorPort | None,
    fields: dict[str, str],
    region: str,
) -> ValidateOutput:
    """Validate parsed fields using the region validator, if available."""
    if validator is None:
        result = ValidationResult(
            passed=True,
            errors=[],
            region=region,
            validated_at=datetime.now(UTC),
        )
        return ValidateOutput(validation_result=result)

    result = await validator.validate(fields)
    return ValidateOutput(validation_result=result)
