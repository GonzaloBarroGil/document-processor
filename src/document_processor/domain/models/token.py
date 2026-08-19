from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from document_processor.domain.models.user import UserRole


class TokenType(StrEnum):
    """The kind of JWT issued by the auth flow."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """The verified claims carried by a JWT."""

    subject: UUID
    role: UserRole
    token_type: TokenType
    jti: str
    issued_at: datetime
    expires_at: datetime


class RefreshToken(BaseModel):
    """A newly issued rotating refresh token and its bookkeeping data."""

    value: str
    jti: str
    expires_at: datetime


class TokenPair(BaseModel):
    """An access token paired with its rotating refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
