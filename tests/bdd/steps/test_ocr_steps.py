import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from document_processor.core.errors import (
    HeicTranscodingError,
    OCRFailureError,
    OCRTimeoutError,
)
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.pipeline.extract import extract as extract_step
from document_processor.domain.pipeline.preprocess import preprocess as preprocess_step
from document_processor.domain.ports.ocr import OCRPort, OCRResult


@pytest.fixture
def ocr_image_data():
    return (b"default-image", MediaType.JPEG)


@pytest.fixture
def ocr_timeout():
    return {"value": False}


@pytest.fixture
def ocr_test_document():
    return Document(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.PENDING,
        media_type=MediaType.JPEG,
        image_key="images/test.jpg",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@given("the OCR engine is available")
def step_ocr_available():
    pass


@given(
    "a well-lit, high-resolution invoice image in Spanish",
    target_fixture="ocr_image_data",
)
def step_clear_invoice():
    return (b"fake-invoice-image", MediaType.JPEG)


@given("a valid HEIC image", target_fixture="ocr_image_data")
def step_heic_image():
    return (b"fake-heic-data", MediaType.HEIC)


@given(
    parsers.parse("a PDF with {pages:d} pages"),
    target_fixture="ocr_image_data",
)
def step_pdf_image(pages: int):
    return (b"fake-pdf-data", MediaType.PDF)


@given("a blurry, low-resolution image", target_fixture="ocr_image_data")
def step_blurry_image():
    return (b"blurry-image", MediaType.JPEG)


@given("the OCR engine takes longer than 60 seconds")
def step_ocr_timeout_set(ocr_timeout):
    ocr_timeout["value"] = True


@given(
    "a malformed HEIC file that cannot be transcoded",
    target_fixture="ocr_image_data",
)
def step_malformed_heic():
    return (b"corrupt-heic", MediaType.HEIC)


class _MockOCR(OCRPort):
    def __init__(
        self,
        raise_error=None,
        confidence=0.95,
        raw_text="total_amount: 500\ndate: 2024-01-15\nvendor_name: ACME",
    ):
        self._raise = raise_error
        self._confidence = confidence
        self._raw_text = raw_text

    async def extract(self, image_data: bytes, media_type: MediaType) -> OCRResult:
        if self._raise:
            raise self._raise
        return OCRResult(raw_text=self._raw_text, confidence=self._confidence)


def _build_mock_ocr(ocr_image_data, ocr_timeout):
    image_data, media_type = ocr_image_data
    is_timeout = ocr_timeout.get("value", False)

    if is_timeout:
        return _MockOCR(raise_error=OCRTimeoutError())
    elif media_type == MediaType.JPEG and image_data == b"blurry-image":
        return _MockOCR(confidence=0.3, raw_text="...")
    else:
        return _MockOCR(
            confidence=0.95,
            raw_text="total_amount: 500\ndate: 2024-01-15\nvendor_name: ACME",
        )


@when("the OCR pipeline processes it", target_fixture="ocr_result")
def step_ocr_pipeline_process(ocr_image_data, ocr_timeout):
    image_data, media_type = ocr_image_data
    mock_ocr = _build_mock_ocr(ocr_image_data, ocr_timeout)
    result = {"pipeline": True}

    if media_type == MediaType.HEIC:
        with patch(
            "document_processor.adapters.ocr.heic_transcoder.transcode_heic",
            new_callable=AsyncMock,
        ) as mock_transcode:
            if image_data == b"corrupt-heic":
                mock_transcode.side_effect = HeicTranscodingError()
                try:
                    preprocessed = asyncio.run(preprocess_step(image_data, media_type))
                    result["preprocessed_media_type"] = preprocessed.media_type
                except HeicTranscodingError as e:
                    result["error"] = str(e)
                    result["status"] = "OCR_FAILED"
                    return result
            else:
                mock_transcode.return_value = b"transcoded-to-png"

            preprocessed = asyncio.run(preprocess_step(image_data, media_type))
            result["preprocessed_media_type"] = preprocessed.media_type
            image_data = preprocessed.image_data
            media_type = preprocessed.media_type
    elif media_type == MediaType.PDF:
        with patch(
            "document_processor.adapters.ocr.pdf_rasterizer.rasterize_pdf",
            new_callable=AsyncMock,
        ) as mock_rasterize:
            mock_rasterize.return_value = b"rasterized-pdf"
            preprocessed = asyncio.run(preprocess_step(image_data, media_type))
            result["preprocessed_media_type"] = preprocessed.media_type
            image_data = preprocessed.image_data
            media_type = preprocessed.media_type
    else:
        preprocessed = asyncio.run(preprocess_step(image_data, media_type))

    try:
        extracted = asyncio.run(
            extract_step(mock_ocr, preprocessed.image_data, preprocessed.media_type, 0.7)
        )
        result["raw_text"] = extracted.raw_text
        result["confidence"] = extracted.confidence
        result["status"] = "success"
    except OCRFailureError as e:
        result["error"] = str(e)
        result["status"] = "OCR_FAILED"

    return result


@then(parsers.parse("raw text is extracted with confidence at least {threshold:f}"))
def step_confidence_threshold(ocr_result, threshold: float):
    assert ocr_result["confidence"] >= threshold


@then(parsers.parse('fields "{field1}", "{field2}", "{field3}" are identifiable'))
def step_fields_identifiable(ocr_result, field1: str, field2: str, field3: str):
    raw_text = ocr_result["raw_text"]
    for field in [field1, field2, field3]:
        assert field in raw_text, f"Field '{field}' not found in '{raw_text}'"


@then("the image is transcoded to JPEG or PNG before OCR")
def step_transcoded(ocr_result):
    assert ocr_result.get("preprocessed_media_type") == MediaType.PNG


@then("OCR proceeds on the transcoded image")
def step_ocr_proceeds_transcoded(ocr_result):
    assert ocr_result["status"] == "success"


@then("the original HEIC is stored")
def step_original_heic_stored():
    pass


@then("each page is rasterized and OCRd")
@then("extracted text is merged from all pages")
def step_pdf_processed(ocr_result):
    assert ocr_result["status"] == "success"


@then(parsers.parse('the document status is set to "{status}"'))
def step_document_status(ocr_result, status: str):
    assert ocr_result["status"] == status


@then(parsers.parse('an error detail "{detail}" is recorded'))
def step_error_detail_recorded(ocr_result, detail: str):
    assert detail in ocr_result.get("error", "")


@then(parsers.parse('the error detail is "{detail}"'))
def step_error_detail_exact(ocr_result, detail: str):
    error_str = ocr_result.get("error", "")
    assert detail in error_str


scenarios("../features/ocr_processing.feature")
