
from document_processor.adapters.validators.ar.afip import (
    validate_cae_format,
    validate_caea_format,
)
from document_processor.adapters.validators.ar.cuit import (
    clean_cuit,
    validate_cuit_digits,
    validate_cuit_format,
)
from document_processor.adapters.validators.ar.iva import (
    validate_iva_breakdown,
)


class TestCUIT:
    def test_clean_cuit_removes_dashes(self) -> None:
        assert clean_cuit("30-12345678-9") == "30123456789"

    def test_clean_cuit_removes_spaces(self) -> None:
        assert clean_cuit(" 30 12345678 9 ") == "30123456789"

    def test_valid_cuit_format(self) -> None:
        assert validate_cuit_format("30-12345678-9") is True

    def test_invalid_cuit_short(self) -> None:
        assert validate_cuit_format("12-34-567") is False

    def test_invalid_cuit_alpha(self) -> None:
        assert validate_cuit_format("30-ABCDEFGH-9") is False

    def test_valid_cuit_digits(self) -> None:
        assert validate_cuit_digits("30-12345678-1") is True

    def test_invalid_cuit_digits(self) -> None:
        assert validate_cuit_digits("30-12345678-9") is False


class TestAFIP:
    def test_valid_cae(self) -> None:
        assert validate_cae_format("12345678901234") is True

    def test_invalid_cae_short(self) -> None:
        assert validate_cae_format("123") is False

    def test_invalid_cae_alpha(self) -> None:
        assert validate_cae_format("1234567890123A") is False

    def test_valid_caea(self) -> None:
        assert validate_caea_format("12345678901234") is True

    def test_invalid_caea_short(self) -> None:
        assert validate_caea_format("123") is False


class TestIVA:
    def test_valid_iva_breakdown(self) -> None:
        fields = {
            "iva_21": "210.00",
            "iva_10_5": "52.50",
            "total": "1762.50",
        }
        errors = validate_iva_breakdown(fields)
        assert errors == []

    def test_iva_breakdown_mismatch(self) -> None:
        fields = {
            "iva_21": "100.00",
            "neto_gravado": "1000.00",
            "total": "1100.00",
        }
        errors = validate_iva_breakdown(fields)
        assert len(errors) == 0

    def test_iva_neto_total_mismatch(self) -> None:
        fields = {
            "iva_21": "100.00",
            "neto_gravado": "800.00",
            "total": "1100.00",
        }
        errors = validate_iva_breakdown(fields)
        assert len(errors) > 0
        assert any(e.rule == "IVA_BREAKDOWN" for e in errors)

    def test_iva_missing_field_no_error(self) -> None:
        fields = {"vendor": "ACME"}
        errors = validate_iva_breakdown(fields)
        assert errors == []
