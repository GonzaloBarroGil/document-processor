from fastapi import Depends, Header, HTTPException

from document_processor.core.errors import AuthenticationError
from document_processor.domain.models.user import User
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService

_document_service: DocumentService | None = None
_auth_service: AuthService | None = None


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
