from datetime import datetime

from pydantic import BaseModel


class ApiKey(BaseModel):
    prefix: str
    hash: str
    created_at: datetime
    revoked: bool
