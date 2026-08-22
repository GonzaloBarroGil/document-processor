from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, HTTPException

from document_processor.core.errors import AuthenticationError
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService
from document_processor.domain.services.quota_service import QuotaService
from document_processor.domain.services.review_service import ReviewService

_document_service: DocumentService | None = None
_auth_service: AuthService | None = None
_review_service: ReviewService | None = None
_export_service: ExportService | None = None
_quota_service: QuotaService | None = None


def set_document_service(service: DocumentService) -> None:
    """Set the application-wide DocumentService instance."""
    global _document_service
    _document_service = service


def get_document_service() -> DocumentService:
    """Return the application-wide DocumentService instance."""
    assert _document_service is not None, "DocumentService not initialized"
    return _document_service


def set_auth_service(service: AuthService) -> None:
    """Set the application-wide AuthService instance."""
    global _auth_service
    _auth_service = service


def get_auth_service() -> AuthService:
    """Return the application-wide AuthService instance."""
    assert _auth_service is not None, "AuthService not initialized"
    return _auth_service


def get_optional_auth_service() -> AuthService | None:
    """Return the application-wide AuthService instance, or None if not configured."""
    return _auth_service


def set_review_service(service: ReviewService) -> None:
    """Set the application-wide ReviewService instance."""
    global _review_service
    _review_service = service


def get_review_service() -> ReviewService:
    """Return the application-wide ReviewService instance."""
    assert _review_service is not None, "ReviewService not initialized"
    return _review_service


def set_export_service(service: ExportService) -> None:
    """Set the application-wide ExportService instance."""
    global _export_service
    _export_service = service


def get_export_service() -> ExportService:
    """Return the application-wide ExportService instance."""
    assert _export_service is not None, "ExportService not initialized"
    return _export_service


def set_quota_service(service: QuotaService | None) -> None:
    """Set the application-wide QuotaService instance."""
    global _quota_service
    _quota_service = service


def get_quota_service() -> QuotaService | None:
    """Return the application-wide QuotaService instance, or None if not configured."""
    return _quota_service


async def get_current_user(
    authorization: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> User:
    """Return the authenticated user identified by the Bearer token."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid credentials")

    token = authorization.removeprefix("Bearer ")
    try:
        return await auth_service.current_user(token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail="Missing or invalid credentials") from e


async def get_optional_current_user(
    authorization: str | None = Header(default=None),
    auth_service: AuthService | None = Depends(get_optional_auth_service),  # noqa: B008
) -> User | None:
    """Return the authenticated user from the Bearer token, or None for machine clients."""
    if authorization is None or not authorization.startswith("Bearer "):
        return None

    if auth_service is None:
        raise HTTPException(status_code=401, detail="Missing or invalid credentials")

    token = authorization.removeprefix("Bearer ")
    try:
        return await auth_service.current_user(token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail="Missing or invalid credentials") from e


def require_roles(*roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Return a dependency requiring the current user to hold one of the given roles."""

    async def _require_role(user: User = Depends(get_current_user)) -> User:  # noqa: B008
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _require_role


require_admin = require_roles(UserRole.ADMIN)
require_reviewer = require_roles(UserRole.ADMIN, UserRole.REVIEWER)
