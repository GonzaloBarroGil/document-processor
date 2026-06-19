from datetime import datetime

from pydantic import BaseModel


class ValidationError(BaseModel):
    field: str
    rule: str
    message: str


class ValidationResult(BaseModel):
    passed: bool
    errors: list[ValidationError]
    region: str
    validated_at: datetime
