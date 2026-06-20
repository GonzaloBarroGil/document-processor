from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from document_processor.core.errors import (
    FileTooLargeError,
    OCRFailureError,
    UnsupportedMediaTypeError,
)
from document_processor.domain.models.document import (
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult
from document_processor.domain.pipeline.extract import extract
from document_processor.domain.pipeline.ingest import (
    IngestInput,
    ingest,
    media_type_to_ext,
)
from document_processor.domain.pipeline.parse import parse
from document_processor.domain.pipeline.persist import persist
from document_processor.domain.pipeline.preprocess import preprocess
from document_processor.domain.pipeline.validate import validate
from document_processor.domain.ports.ocr import OCRPort, OCRResult


class TestMediaTypeToExt:
    def test_jpeg(self) -> None:
        assert media_type_to_ext(MediaType.JPEG) == "jpg"

    def test_png(self) -> None:
        assert media_type_to_ext(MediaType.PNG) == "png"

    def test_heic(self) -> None:
        assert media_type_to_ext(MediaType.HEIC) == "heic"

    def test_pdf(self) -> None:
        assert media_type_to_ext(MediaType.PDF) == "pdf"


class TestIngest:
    def test_valid_jpeg(self) -> None:
        input_ = IngestInput(
            file_bytes=b"fake-image",
            filename="invoice.jpg",
            document_type=DocumentType.INVOICE,
            region="AR",
            media_type=MediaType.JPEG,
            max_size_bytes=1024,
            allowed_media_types=[MediaType.JPEG, MediaType.PNG],
        )
        output = ingest(input_)
        assert isinstance(output.document.id, UUID)
        assert output.document.type == DocumentType.INVOICE
        assert output.document.region == "AR"
        assert output.document.status == DocumentStatus.PENDING
        assert output.document.media_type == MediaType.JPEG
        assert output.image_key.endswith(".jpg")

    def test_unsupported_media_type(self) -> None:
        input_ = IngestInput(
            file_bytes=b"fake",
            filename="file.tar",
            document_type=DocumentType.INVOICE,
            region="AR",
            media_type=MediaType.PDF,
            max_size_bytes=1024,
            allowed_media_types=[MediaType.JPEG],
        )
        with pytest.raises(UnsupportedMediaTypeError):
            ingest(input_)

    def test_file_too_large(self) -> None:
        input_ = IngestInput(
            file_bytes=b"x" * 100,
            filename="big.jpg",
            document_type=DocumentType.INVOICE,
            region="AR",
            media_type=MediaType.JPEG,
            max_size_bytes=50,
            allowed_media_types=[MediaType.JPEG],
        )
        with pytest.raises(FileTooLargeError):
            ingest(input_)


class TestPreprocess:
    async def test_jpeg_passthrough(self) -> None:
        result = await preprocess(b"jpeg-data", MediaType.JPEG)
        assert result.image_data == b"jpeg-data"
        assert result.media_type == MediaType.JPEG

    async def test_png_passthrough(self) -> None:
        result = await preprocess(b"png-data", MediaType.PNG)
        assert result.image_data == b"png-data"
        assert result.media_type == MediaType.PNG


class TestExtract:
    async def test_successful_extraction(self) -> None:
        ocr_port = MagicMock(spec=OCRPort)
        ocr_port.extract = AsyncMock(
            return_value=OCRResult(raw_text="Total: 1500.00", confidence=0.85)
        )

        result = await extract(ocr_port, b"image", MediaType.JPEG, 0.7)

        assert result.raw_text == "Total: 1500.00"
        assert result.confidence == 0.85
        ocr_port.extract.assert_called_once()

    async def test_low_confidence_raises(self) -> None:
        ocr_port = MagicMock(spec=OCRPort)
        ocr_port.extract = AsyncMock(
            return_value=OCRResult(raw_text="blurry", confidence=0.3)
        )

        with pytest.raises(OCRFailureError):
            await extract(ocr_port, b"image", MediaType.JPEG, 0.7)


class TestParse:
    def test_parse_simple_text(self) -> None:
        raw_text = "total_amount: 1500.00\ndate: 2024-01-15\nvendor_name: ACME S.A."
        result = parse(raw_text, 0.85)

        assert result.parsed_data.confidence == 0.85
        assert result.parsed_data.raw_text == raw_text
        assert result.parsed_data.fields["total_amount"] == "1500.00"
        assert result.parsed_data.fields["date"] == "2024-01-15"
        assert result.parsed_data.fields["vendor_name"] == "ACME S.A."

    def test_parse_empty_text(self) -> None:
        result = parse("", 0.0)
        assert result.parsed_data.raw_text == ""
        assert result.parsed_data.fields == {}

    def test_parse_no_colon_line(self) -> None:
        result = parse("ACME Invoice 12345", 0.9)
        assert "acme" in result.parsed_data.fields
        assert result.parsed_data.fields["acme"] == "Invoice 12345"


class TestValidate:
    async def test_with_validator(self) -> None:
        validator = MagicMock()
        validator.validate = AsyncMock(
            return_value=ValidationResult(
                passed=True,
                errors=[],
                region="AR",
                validated_at=datetime.now(UTC),
            )
        )

        result = await validate(
            validator, {"cuit_emisor": "30-12345678-9"}, "AR"
        )

        assert result.validation_result.passed is True
        validator.validate.assert_called_once()

    async def test_without_validator_passthrough(self) -> None:
        result = await validate(None, {}, "XX")
        assert result.validation_result.passed is True
        assert result.validation_result.region == "XX"


class TestPersist:
    async def test_persist_success(self) -> None:
        repo = MagicMock()
        repo.update_parsed_data = AsyncMock()
        repo.update_status = AsyncMock()

        parsed = ParsedData(raw_text="test", confidence=0.9, fields={})
        doc_id = UUID("00000000-0000-0000-0000-000000000001")

        result = await persist(
            repo, doc_id, parsed, None, DocumentStatus.COMPLETED
        )

        assert result.success is True
        repo.update_parsed_data.assert_called_once()
        repo.update_status.assert_called_once_with(
            document_id=doc_id, status=DocumentStatus.COMPLETED
        )
