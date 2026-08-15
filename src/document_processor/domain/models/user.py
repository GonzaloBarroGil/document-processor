from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"


class User(BaseModel):
    id: UUID
    username: str
    password_hash: str
    role: UserRole = UserRole.REVIEWER
    created_at: datetime
    updated_at: datetime
