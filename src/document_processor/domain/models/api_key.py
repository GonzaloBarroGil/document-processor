from datetime import datetime

from pydantic import BaseModel


class ApiKey(BaseModel):
    """A persisted API key for machine clients."""

    prefix: str
    hash: str
    label: str | None = None
    created_at: datetime
    revoked: bool


class CreatedApiKey(BaseModel):
    """A newly issued API key whose raw value is shown only once."""

    key: str
    prefix: str
    label: str | None
