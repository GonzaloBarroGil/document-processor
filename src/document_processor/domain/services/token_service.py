import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from document_processor.core.config import settings
from document_processor.core.errors import InvalidTokenError
from document_processor.domain.models.token import (
    RefreshToken,
    TokenPayload,
    TokenType,
)
from document_processor.domain.models.user import UserRole

_REQUIRED_CLAIMS = ["sub", "role", "type", "jti", "iat", "exp"]


class TokenService:
    """Issues and verifies access and rotating refresh JWTs."""

    def issue_access_token(self, subject: UUID, role: UserRole) -> str:
        """Return a signed access token for the given user and role."""
        return self._encode(subject, role, TokenType.ACCESS, settings.access_token_ttl_seconds)

    def issue_refresh_token(
        self, subject: UUID, role: UserRole, jti: str | None = None
    ) -> RefreshToken:
        """Return a signed refresh token plus its jti and expiry."""
        token_jti = jti or uuid.uuid4().hex
        now = datetime.now(UTC)
        expires_at = self._expires_at(now, settings.refresh_token_ttl_seconds)
        token = self._encode(
            subject,
            role,
            TokenType.REFRESH,
            settings.refresh_token_ttl_seconds,
            token_jti,
            now,
        )
        return RefreshToken(value=token, jti=token_jti, expires_at=expires_at)

    def decode(self, token: str, expected_type: TokenType) -> TokenPayload:
        """Verify and decode a token, requiring it to be of the given type."""
        try:
            claims = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError from e

        try:
            payload = TokenPayload(
                subject=UUID(claims["sub"]),
                role=UserRole(claims["role"]),
                token_type=TokenType(claims["type"]),
                jti=str(claims["jti"]),
                issued_at=datetime.fromtimestamp(claims["iat"], tz=UTC),
                expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
            )
        except (KeyError, ValueError) as e:
            raise InvalidTokenError from e

        if payload.token_type != expected_type:
            raise InvalidTokenError

        return payload

    @staticmethod
    def hash_token(token: str) -> str:
        """Return the SHA-256 hex digest of a raw token for opaque storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _expires_at(now: datetime, ttl_seconds: int) -> datetime:
        return datetime.fromtimestamp(
            int((now + timedelta(seconds=ttl_seconds)).timestamp()), tz=UTC
        )

    def _encode(
        self,
        subject: UUID,
        role: UserRole,
        token_type: TokenType,
        ttl_seconds: int,
        jti: str | None = None,
        now: datetime | None = None,
    ) -> str:
        now = now or datetime.now(UTC)
        expires_at = self._expires_at(now, ttl_seconds)
        return jwt.encode(
            {
                "sub": str(subject),
                "role": role.value,
                "type": token_type.value,
                "jti": jti or uuid.uuid4().hex,
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
