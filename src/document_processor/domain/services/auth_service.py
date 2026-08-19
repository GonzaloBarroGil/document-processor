from document_processor.core.config import settings
from document_processor.core.errors import InvalidCredentialsError, InvalidTokenError
from document_processor.domain.models.token import TokenPair, TokenType
from document_processor.domain.models.user import User
from document_processor.domain.ports.auth import AuthPort
from document_processor.domain.ports.refresh_token import RefreshTokenRepositoryPort
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


class AuthService:
    """Authenticates users and rotates refresh tokens."""

    def __init__(
        self,
        user_repository: AuthPort,
        refresh_token_repository: RefreshTokenRepositoryPort,
        tokens: TokenService,
        passwords: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository
        self._tokens = tokens
        self._passwords = passwords

    async def authenticate(self, username: str, password: str) -> TokenPair:
        """Verify credentials and issue a fresh access/refresh token pair."""
        user = await self._user_repository.get_user_by_username(username)
        if user is None or not self._passwords.verify(password, user.password_hash):
            raise InvalidCredentialsError
        return await self._issue_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate a valid refresh token into a new token pair."""
        payload = self._tokens.decode(refresh_token, TokenType.REFRESH)
        token_hash = self._tokens.hash_token(refresh_token)

        if not await self._refresh_token_repository.is_active(token_hash):
            raise InvalidTokenError

        user = await self._user_repository.get_user_by_id(payload.subject)
        if user is None:
            raise InvalidTokenError

        await self._refresh_token_repository.revoke(token_hash)
        return await self._issue_pair(user)

    async def _issue_pair(self, user: User) -> TokenPair:
        access_token = self._tokens.issue_access_token(user.id, user.role)
        refresh = self._tokens.issue_refresh_token(user.id, user.role)

        await self._refresh_token_repository.save(
            token_hash=self._tokens.hash_token(refresh.value),
            user_id=user.id,
            expires_at=refresh.expires_at,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh.value,
            expires_in=settings.access_token_ttl_seconds,
        )
