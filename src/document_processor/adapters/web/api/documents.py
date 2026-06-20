from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from starlette.responses import JSONResponse, Response

from document_processor.adapters.web.api.deps import get_document_service
from document_processor.core.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    ImageExpiredError,
    UnsupportedMediaTypeError,
)
from document_processor.domain.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("", status_code=202, response_model=None)  # type: ignore[call-overload]
async def ingest_document(
    file: UploadFile = File(...),  # noqa: B008
    type: str = Form(...),
    region: str = Form(...),
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> dict[str, str] | JSONResponse:
    try:
        content = await file.read()
        media_type = file.content_type or "application/octet-stream"

        doc = await service.ingest_document(
            file_bytes=content,
            filename=file.filename or "unknown",
            document_type_value=type,
            region=region or "AR",
            media_type_value=media_type,
        )
        return {
            "document_id": str(doc.id),
            "status": doc.status.value,
            "image_key": doc.image_key,
        }
    except UnsupportedMediaTypeError as e:
        return JSONResponse(status_code=422, content={"detail": str(e)})
    except FileTooLargeError as e:
        return JSONResponse(status_code=413, content={"detail": str(e)})


@router.get("/{document_id}", response_model=None)
async def get_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> dict[str, Any] | JSONResponse:
    try:
        doc = await service.get_document(document_id)
        return doc.model_dump(mode="json")
    except DocumentNotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})


@router.get("")
async def list_documents(
    status: str | None = Query(None),
    type: str | None = Query(None),
    region: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> dict[str, Any]:
    docs, total = await service.list_documents(
        status=status, type=type, region=region, page=page, size=size
    )
    pages = -(-total // size) if total > 0 else 1
    return {
        "items": [doc.model_dump(mode="json") for doc in docs],
        "total": total,
        "page": page,
        "pages": pages,
    }


@router.get("/{document_id}/image", response_model=None)
async def get_document_image(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> Response | JSONResponse:
    try:
        image_data = await service.get_document_image(document_id)
        return Response(content=image_data, media_type="image/jpeg")
    except DocumentNotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})
    except ImageExpiredError as e:
        return JSONResponse(status_code=410, content={"detail": str(e)})
