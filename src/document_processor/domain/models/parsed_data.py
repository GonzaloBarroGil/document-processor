from pydantic import BaseModel, Field


class RecipientData(BaseModel):
    """A single recipient parsed from a payment document."""

    name: str | None = None
    cuit: str | None = None
    individual_amount: float | None = None
    fields: dict[str, str] = Field(default_factory=dict)


class ParsedData(BaseModel):
    """Text and fields extracted from a document image."""

    raw_text: str
    confidence: float
    fields: dict[str, str] = Field(default_factory=dict)
    recipients: list[RecipientData] | None = None
