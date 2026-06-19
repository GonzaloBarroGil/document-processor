import logging
from uuid import UUID

from document_processor.core.config import settings
from document_processor.core.errors import (
    DocumentNotFoundError,
    ImageExpiredError,
    OCRFailureError,
    UnsupportedMediaTypeError,
)
from document_processor.domain.models.document import Document, DocumentStatus
from document_processor.domain.models.document import DocumentType, MediaType
from document_processor.domain.pipeline.extract import extract
from document_processor.domain.pipeline.ingest import IngestInput, IngestOutput, ingest
from document_processor.domain.pipeline.parse import parse
from document_processor.domain.pipeline.persist import persist
from document_processor.domain.pipeline.preprocess import preprocess
from document_processor.domain.pipeline.validate import validate as validate_step
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)
from document_processor.domain.ports.ocr import OCRPort
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.domain.ports.storage import StoragePort

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepositoryPort,
        storage: StoragePort,
        ocr: OCRPort,
        validator_registry: dict[str, RegionValidatorPort],
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._ocr = ocr
        self._validator_registry = validator_registry

    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        document_type_value: str,
        region: str,
        media_type_value: str,
    ) -> Document:
        try:
            media_type = MediaType(media_type_value)
            document_type = DocumentType(document_type_value)
        except ValueError as e:
            raise UnsupportedMediaTypeError(media_type_value) from e

        allowed_media_types = [
            MediaType(mt) for mt in settings.allowed_media_types
        ]

        input_ = IngestInput(
            file_bytes=file_bytes,
            filename=filename,
            document_type=document_type,
            region=region,
            media_type=media_type,
            max_size_bytes=settings.max_image_size_bytes,
            allowed_media_types=allowed_media_types,
        )

        output = ingest(input_)

        await self._repository.create(output.document)
        await self._storage.store(
            key=output.image_key,
            data=file_bytes,
            content_type=media_type_value,
        )

        return output.document

    async def get_document(self, document_id: UUID) -> Document:
        doc = await self._repository.get_by_id(document_id)
        if doc is None:
            raise DocumentNotFoundError(str(document_id))
        return doc

    async def list_documents(
        self,
        status: str | None = None,
        type: str | None = None,
        region: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Document], int]:
        doc_status = DocumentStatus(status) if status else None
        return await self._repository.list_documents(
            status=doc_status, type=type, region=region, page=page, size=size
        )

    async def get_document_image(self, document_id: UUID) -> bytes:
        doc = await self._repository.get_by_id(document_id)
        if doc is None:
            raise DocumentNotFoundError(str(document_id))
        if doc.status == DocumentStatus.IMAGE_EXPIRED:
            raise ImageExpiredError(str(document_id))

        image_data = await self._storage.retrieve(doc.image_key)
        if image_data is None:
            raise DocumentNotFoundError(str(document_id))
        return image_data

    async def process_document(self, document: Document) -> None:
        try:
            await self._repository.update_status(
                document.id, DocumentStatus.OCR_IN_PROGRESS
            )

            image_data = await self._storage.retrieve(document.image_key)
            if image_data is None:
                raise DocumentNotFoundError(str(document.id))

            preprocessed = await preprocess(image_data, document.media_type)

            extracted = await extract(
                self._ocr,
                preprocessed.image_data,
                preprocessed.media_type,
                settings.ocr_confidence_threshold,
            )

            parsed = parse(extracted.raw_text, extracted.confidence)

            await self._repository.update_status(
                document.id, DocumentStatus.VALIDATING
            )

            validator = self._validator_registry.get(document.region)
            validated = await validate_step(
                validator, parsed.parsed_data.fields, document.region
            )

            status = (
                DocumentStatus.COMPLETED
                if validated.validation_result.passed
                else DocumentStatus.VALIDATION_FAILED
            )

            await persist(
                self._repository,
                document.id,
                parsed.parsed_data,
                validated.validation_result,
                status,
            )

        except OCRFailureError as e:
            logger.error(
                "OCR failed for document %s: %s", document.id, e.detail
            )
            await self._repository.update_status(
                document.id, DocumentStatus.OCR_FAILED
            )
