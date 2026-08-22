from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.responses import Response

from document_processor.adapters.web.api.deps import get_api_key_service, require_admin
from document_processor.core.errors import ApiKeyNotFoundError
from document_processor.domain.models.api_key import CreatedApiKey
from document_processor.domain.models.user import User
from document_processor.domain.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


class ApiKeyCreateRequest(BaseModel):
    """A label for a new machine-client API key."""

    label: str | None = None


class ApiKeyView(BaseModel):
    """A machine-client API key, without its secret material."""

    prefix: str
    label: str | None
    created_at: datetime
    revoked: bool


class ApiKeyList(BaseModel):
    """A list of machine-client API keys."""

    items: list[ApiKeyView]


@router.post("", status_code=201, response_model=CreatedApiKey)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    user: User = Depends(require_admin),  # noqa: B008
    service: ApiKeyService = Depends(get_api_key_service),  # noqa: B008
) -> CreatedApiKey:
    """Create a machine-client API key (raw key shown once)."""
    return await service.create_key(payload.label)


@router.get("", response_model=ApiKeyList)
async def list_api_keys(
    user: User = Depends(require_admin),  # noqa: B008
    service: ApiKeyService = Depends(get_api_key_service),  # noqa: B008
) -> ApiKeyList:
    """List machine-client API keys."""
    keys = await service.list_keys()
    return ApiKeyList(
        items=[
            ApiKeyView(
                prefix=key.prefix,
                label=key.label,
                created_at=key.created_at,
                revoked=key.revoked,
            )
            for key in keys
        ]
    )


@router.post("/{prefix}/revoke", status_code=204)
async def revoke_api_key(
    prefix: str,
    user: User = Depends(require_admin),  # noqa: B008
    service: ApiKeyService = Depends(get_api_key_service),  # noqa: B008
) -> Response:
    """Revoke a machine-client API key."""
    try:
        await service.revoke(prefix)
    except ApiKeyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=204)
