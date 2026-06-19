from typing import Optional

from pydantic import BaseModel, Field


class RecipientData(BaseModel):
    name: Optional[str] = None
    cuit: Optional[str] = None
    individual_amount: Optional[float] = None
    fields: dict[str, str] = Field(default_factory=dict)


class ParsedData(BaseModel):
    raw_text: str
    confidence: float
    fields: dict[str, str] = Field(default_factory=dict)
    recipients: Optional[list[RecipientData]] = None
