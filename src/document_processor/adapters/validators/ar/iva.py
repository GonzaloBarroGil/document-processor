
from document_processor.domain.models.validation import ValidationError


def validate_iva_breakdown(fields: dict[str, str]) -> list[ValidationError]:
    errors: list[ValidationError] = []

    total_str = fields.get("total")
    if total_str is None:
        return errors

    try:
        total = float(total_str)
    except ValueError:
        return errors

    iva_sum = 0.0
    for key, value in fields.items():
        if key.startswith("iva_"):
            try:
                iva_sum += float(value)
            except ValueError:
                continue

    if iva_sum == 0.0:
        return errors

    neto_str = fields.get("neto_gravado")
    if neto_str:
        try:
            neto = float(neto_str)
            expected = neto + iva_sum
            if abs(expected - total) > 0.02:
                errors.append(
                    ValidationError(
                        field="total",
                        rule="IVA_BREAKDOWN",
                        message=f"Total {total} does not match neto + IVA ({expected})",
                    )
                )
        except ValueError:
            pass
    elif iva_sum > total + 0.01:
        errors.append(
            ValidationError(
                field="total",
                rule="IVA_BREAKDOWN",
                message=f"IVA sum ({iva_sum}) exceeds total ({total})",
            )
        )

    return errors
