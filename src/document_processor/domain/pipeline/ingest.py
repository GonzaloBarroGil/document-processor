from datetime import UTC, datetime
from uuid import uuid4

from document_processor.core.errors import FileTooLargeError, UnsupportedMediaTypeError
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)


class IngestInput:
    def __init__(
        self,
        file_bytes: bytes,
        filename: str,
        document_type: DocumentType,
        region: str,
        media_type: MediaType,
        max_size_bytes: int,
        allowed_media_types: list[MediaType],
    ) -> None:
        self.file_bytes = file_bytes
        self.filename = filename
        self.document_type = document_type
        self.region = region
        self.media_type = media_type
        self.max_size_bytes = max_size_bytes
        self.allowed_media_types = allowed_media_types


class IngestOutput:
    def __init__(self, document: Document, image_key: str, image_ext: str) -> None:
        self.document = document
        self.image_key = image_key
        self.image_ext = image_ext


def media_type_to_ext(media_type: MediaType) -> str:
    mapping = {
        MediaType.JPEG: "jpg",
        MediaType.PNG: "png",
        MediaType.HEIC: "heic",
        MediaType.PDF: "pdf",
    }
    return mapping[media_type]


def ingest(input_: IngestInput) -> IngestOutput:
    if input_.media_type not in input_.allowed_media_types:
        raise UnsupportedMediaTypeError(input_.media_type.value)

    if len(input_.file_bytes) > input_.max_size_bytes:
        raise FileTooLargeError(len(input_.file_bytes), input_.max_size_bytes)

    document_id = uuid4()
    image_ext = media_type_to_ext(input_.media_type)
    image_key = f"{document_id}.{image_ext}"
    now = datetime.now(UTC)

    document = Document(
        id=document_id,
        type=input_.document_type,
        region=input_.region,
        status=DocumentStatus.PENDING,
        media_type=input_.media_type,
        image_key=image_key,
        parsed_data=None,
        validation_result=None,
        error_detail=None,
        created_at=now,
        updated_at=now,
    )

    return IngestOutput(document=document, image_key=image_key, image_ext=image_ext)
