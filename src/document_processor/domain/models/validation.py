from datetime import datetime

from pydantic import BaseModel


class ValidationError(BaseModel):
    """A single field-level validation failure."""

    field: str
    rule: str
    message: str


class ValidationResult(BaseModel):
    """The outcome of validating a document's parsed fields."""

    passed: bool
    errors: list[ValidationError]
    region: str
    validated_at: datetime
