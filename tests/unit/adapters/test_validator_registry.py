from unittest.mock import MagicMock

import pytest

from document_processor.adapters.validators.registry import ValidatorRegistry


class TestValidatorRegistry:
    @pytest.fixture
    def registry(self) -> ValidatorRegistry:
        return ValidatorRegistry()

    def test_get_nonexistent_returns_none(self, registry: ValidatorRegistry) -> None:
        assert registry.get("XX") is None

    def test_register_and_get(self, registry: ValidatorRegistry) -> None:
        validator = MagicMock()
        validator.region_code = "XX"

        registry.register("XX", validator)
        assert registry.get("XX") is validator
