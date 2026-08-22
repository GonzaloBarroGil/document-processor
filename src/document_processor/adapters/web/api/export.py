from uuid import UUID

from fastapi import APIRouter, Depends, Header
from starlette.responses import JSONResponse, Response

from document_processor.adapters.web.api.deps import (
    get_export_service,
    get_optional_current_user,
)
from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.user import User
from document_processor.domain.services.export_service import ExportService

router = APIRouter(tags=["documents"])


@router.get("/api/v1/documents/{document_id}/export", response_model=None)
async def export_document(
    document_id: UUID,
    accept: str | None = Header(default=None),
    service: ExportService = Depends(get_export_service),  # noqa: B008
    user: User | None = Depends(get_optional_current_user),  # noqa: B008
) -> Response | JSONResponse:
    """Return a flattened export of the document's extracted data (JSON or CSV)."""
    try:
        export = await service.export(document_id)
    except DocumentNotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})

    if accept is not None and "text/csv" in accept:
        return Response(content=service.to_csv(export), media_type="text/csv")

    return Response(content=export.model_dump_json(), media_type="application/json")
