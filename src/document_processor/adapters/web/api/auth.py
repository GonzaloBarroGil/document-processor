from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.responses import Response

from document_processor.adapters.web.api.deps import get_auth_service, get_current_user
from document_processor.core.errors import InvalidCredentialsError, InvalidTokenError
from document_processor.domain.models.token import TokenPair
from document_processor.domain.models.user import User
from document_processor.domain.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Credentials submitted for password authentication."""

    username: str
    password: str


class RefreshRequest(BaseModel):
    """A refresh token submitted for rotation."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """An optional refresh token to revoke on logout."""

    refresh_token: str | None = None


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> TokenPair:
    """Exchange credentials for an access + refresh token pair."""
    try:
        return await auth_service.authenticate(payload.username, payload.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail="Invalid credentials") from e


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> TokenPair:
    """Rotate a refresh token for a new token pair."""
    try:
        return await auth_service.refresh(payload.refresh_token)
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token") from e


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:  # noqa: B008
    """Return the authenticated user."""
    return {"id": str(user.id), "username": user.username, "role": user.role.value}


@router.post("/logout", status_code=204)
async def logout(
    payload: LogoutRequest | None = None,
    user: User = Depends(get_current_user),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> Response:
    """Invalidate the current refresh token, if one is supplied."""
    await auth_service.logout(payload.refresh_token if payload is not None else None)
    return Response(status_code=204)
