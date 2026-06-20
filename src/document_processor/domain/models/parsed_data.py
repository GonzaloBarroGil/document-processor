
from pydantic import BaseModel, Field


class RecipientData(BaseModel):
    name: str | None = None
    cuit: str | None = None
    individual_amount: float | None = None
    fields: dict[str, str] = Field(default_factory=dict)


class ParsedData(BaseModel):
    raw_text: str
    confidence: float
    fields: dict[str, str] = Field(default_factory=dict)
    recipients: list[RecipientData] | None = None
