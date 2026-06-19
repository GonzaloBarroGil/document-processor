from abc import ABC, abstractmethod

from document_processor.domain.models.validation import ValidationResult


class RegionValidatorPort(ABC):
    @property
    @abstractmethod
    def region_code(self) -> str:
        ...

    @abstractmethod
    async def validate(self, fields: dict[str, str]) -> ValidationResult:
        ...
