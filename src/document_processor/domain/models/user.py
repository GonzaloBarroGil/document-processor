from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class UserRole(StrEnum):
    """Access role assigned to a human user."""

    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"


class User(BaseModel):
    """A human user who authenticates to the web and mobile apps."""

    id: UUID
    username: str
    password_hash: str
    role: UserRole = UserRole.REVIEWER
    created_at: datetime
    updated_at: datetime
