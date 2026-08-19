from datetime import datetime

from pydantic import BaseModel


class ApiKey(BaseModel):
    """A persisted API key for machine clients."""

    prefix: str
    hash: str
    created_at: datetime
    revoked: bool
