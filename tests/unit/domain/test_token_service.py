import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from document_processor.core.config import settings
from document_processor.core.errors import InvalidTokenError
from document_processor.domain.models.token import TokenType
from document_processor.domain.models.user import UserRole
from document_processor.domain.services.token_service import TokenService


def _craft_token(exp_delta: timedelta, iat_delta: timedelta = timedelta(0)) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "REVIEWER",
            "type": "access",
            "jti": "crafted",
            "iat": int((now + iat_delta).timestamp()),
            "exp": int((now + exp_delta).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


class TestTokenService:
    @pytest.fixture
    def service(self) -> TokenService:
        return TokenService()

    def test_issue_access_token_decodes(self, service: TokenService) -> None:
        subject = uuid4()
        token = service.issue_access_token(subject, UserRole.ADMIN)

        payload = service.decode(token, TokenType.ACCESS)
        assert payload.subject == subject
        assert payload.role == UserRole.ADMIN
        assert payload.token_type == TokenType.ACCESS
        assert payload.jti

    def test_issue_refresh_token_decodes_with_matching_jti(self, service: TokenService) -> None:
        subject = uuid4()
        issued = service.issue_refresh_token(subject, UserRole.REVIEWER)

        payload = service.decode(issued.value, TokenType.REFRESH)
        assert payload.subject == subject
        assert payload.token_type == TokenType.REFRESH
        assert payload.jti == issued.jti
        assert payload.expires_at == issued.expires_at

    def test_refresh_token_can_supply_explicit_jti(self, service: TokenService) -> None:
        subject = uuid4()
        issued = service.issue_refresh_token(subject, UserRole.REVIEWER, jti="fixed-jti")
        assert issued.jti == "fixed-jti"

    def test_decode_rejects_wrong_type(self, service: TokenService) -> None:
        token = service.issue_access_token(uuid4(), UserRole.REVIEWER)

        with pytest.raises(InvalidTokenError):
            service.decode(token, TokenType.REFRESH)

    def test_decode_rejects_tampered_token(self, service: TokenService) -> None:
        token = service.issue_access_token(uuid4(), UserRole.REVIEWER)
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

        with pytest.raises(InvalidTokenError):
            service.decode(tampered, TokenType.ACCESS)

    def test_decode_rejects_expired_token(self, service: TokenService) -> None:
        with pytest.raises(InvalidTokenError):
            service.decode(_craft_token(timedelta(minutes=-1)), TokenType.ACCESS)

    def test_decode_rejects_malformed_claims(self, service: TokenService) -> None:
        token = jwt.encode(
            {
                "sub": "not-a-uuid",
                "role": "REVIEWER",
                "type": "access",
                "jti": "x",
                "iat": 0,
                "exp": 4102444800,
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(InvalidTokenError):
            service.decode(token, TokenType.ACCESS)

    def test_hash_token_is_sha256_hex(self, service: TokenService) -> None:
        assert service.hash_token("abc") == hashlib.sha256(b"abc").hexdigest()
