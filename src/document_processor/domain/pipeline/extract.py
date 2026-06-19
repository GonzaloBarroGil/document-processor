from document_processor.core.errors import OCRFailureError
from document_processor.domain.models.document import MediaType
from document_processor.domain.ports.ocr import OCRPort


class ExtractOutput:
    def __init__(self, raw_text: str, confidence: float) -> None:
        self.raw_text = raw_text
        self.confidence = confidence


async def extract(
    ocr_port: OCRPort,
    image_data: bytes,
    media_type: MediaType,
    confidence_threshold: float,
) -> ExtractOutput:
    result = await ocr_port.extract(image_data, media_type)

    if result.confidence < confidence_threshold:
        raise OCRFailureError(
            f"Low confidence extraction: {result.confidence:.2f} < {confidence_threshold}"
        )

    return ExtractOutput(raw_text=result.raw_text, confidence=result.confidence)
