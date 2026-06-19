from datetime import datetime, timezone

from document_processor.domain.models.validation import (
    ValidationResult,
)
from document_processor.domain.ports.region_validator import RegionValidatorPort


class ValidateOutput:
    def __init__(self, validation_result: ValidationResult) -> None:
        self.validation_result = validation_result


async def validate(
    validator: RegionValidatorPort | None,
    fields: dict[str, str],
    region: str,
) -> ValidateOutput:
    if validator is None:
        result = ValidationResult(
            passed=True,
            errors=[],
            region=region,
            validated_at=datetime.now(timezone.utc),
        )
        return ValidateOutput(validation_result=result)

    result = await validator.validate(fields)
    return ValidateOutput(validation_result=result)
