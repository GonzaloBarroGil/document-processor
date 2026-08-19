from abc import ABC, abstractmethod

from document_processor.domain.models.validation import ValidationResult


class RegionValidatorPort(ABC):
    """Port for validating parsed fields against regional rules."""

    @property
    @abstractmethod
    def region_code(self) -> str:
        """Return the ISO region code this validator handles."""
        ...

    @abstractmethod
    async def validate(self, fields: dict[str, str]) -> ValidationResult:
        """Validate the parsed fields and return the result."""
        ...
