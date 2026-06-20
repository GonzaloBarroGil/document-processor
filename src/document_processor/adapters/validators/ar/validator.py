from datetime import datetime, timezone

from document_processor.domain.models.validation import (
    ValidationError,
    ValidationResult,
)
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.adapters.validators.ar.afip import (
    validate_cae_format,
    validate_caea_format,
)
from document_processor.adapters.validators.ar.cuit import (
    clean_cuit,
    validate_cuit_digits,
    validate_cuit_format,
)
from document_processor.adapters.validators.ar.iva import validate_iva_breakdown


class ArgentinaValidator(RegionValidatorPort):
    @property
    def region_code(self) -> str:
        return "AR"

    async def validate(self, fields: dict[str, str]) -> ValidationResult:
        errors: list[ValidationError] = []

        errors.extend(self._validate_cuit(fields))
        errors.extend(self._validate_afip(fields))
        errors.extend(validate_iva_breakdown(fields))

        passed = len(errors) == 0

        return ValidationResult(
            passed=passed,
            errors=errors,
            region="AR",
            validated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _validate_cuit(fields: dict[str, str]) -> list[ValidationError]:
        errors: list[ValidationError] = []

        for field_name in ("cuit_emisor", "cuit_receptor", "cuit", "cuil"):
            value = fields.get(field_name)
            if value is None:
                continue

            if not validate_cuit_format(value):
                errors.append(
                    ValidationError(
                        field=field_name,
                        rule="CUIT_FORMAT",
                        message=f"Invalid CUIT format: {value}",
                    )
                )
                continue

            if not validate_cuit_digits(value):
                errors.append(
                    ValidationError(
                        field=field_name,
                        rule="CUIT_CHECK_DIGIT",
                        message=f"Invalid CUIT check digit: {value}",
                    )
                )

        return errors

    @staticmethod
    def _validate_afip(fields: dict[str, str]) -> list[ValidationError]:
        errors: list[ValidationError] = []

        comprobante = fields.get("tipo_comprobante")
        cae = fields.get("cae")
        caea = fields.get("caea")

        if cae:
            if not validate_cae_format(cae):
                errors.append(
                    ValidationError(
                        field="cae",
                        rule="CAE_FORMAT",
                        message="CAE must be 14 digits",
                    )
                )
        elif caea:
            if not validate_caea_format(caea):
                errors.append(
                    ValidationError(
                        field="caea",
                        rule="CAEA_FORMAT",
                        message="CAEA must be 14 digits",
                    )
                )
        elif comprobante and comprobante in ("A", "B", "C"):
            errors.append(
                ValidationError(
                    field="cae",
                    rule="CAE_REQUIRED",
                    message=f"CAE is required for comprobante type {comprobante}",
                )
            )

        return errors
