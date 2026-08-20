from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from starlette.responses import JSONResponse

from document_processor.adapters.web.api.deps import (
    get_review_service,
    require_reviewer,
)
from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.document import ReviewAction
from document_processor.domain.models.user import User
from document_processor.domain.services.review_service import ReviewService

router = APIRouter(tags=["review"])


class ReviewRequest(BaseModel):
    """A human review decision on a document."""

    action: ReviewAction
    edited_fields: dict[str, str] | None = None
    comment: str | None = None


@router.patch("/api/v1/documents/{document_id}/review", response_model=None)
async def review_document(
    document_id: UUID,
    payload: ReviewRequest,
    user: User = Depends(require_reviewer),  # noqa: B008
    service: ReviewService = Depends(get_review_service),  # noqa: B008
) -> dict[str, Any] | JSONResponse:
    """Record a manual review decision on the given document."""
    try:
        document = await service.review(
            document_id=document_id,
            reviewer_id=user.id,
            action=payload.action,
            edited_fields=payload.edited_fields,
        )
        return document.model_dump(mode="json")
    except DocumentNotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})


@router.get("/api/v1/review/queue", response_model=None)
async def review_queue(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_reviewer),  # noqa: B008
    service: ReviewService = Depends(get_review_service),  # noqa: B008
) -> dict[str, Any]:
    """Return a paginated list of documents awaiting review."""
    documents, total = await service.list_review_queue(page=page, size=size)
    pages = -(-total // size) if total > 0 else 1
    return {
        "items": [document.model_dump(mode="json") for document in documents],
        "total": total,
        "page": page,
        "pages": pages,
    }
