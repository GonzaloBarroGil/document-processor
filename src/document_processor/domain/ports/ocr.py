from abc import ABC, abstractmethod

from document_processor.domain.models.document import MediaType


class OCRResult:
    """Text and confidence produced by an OCR engine."""

    def __init__(self, raw_text: str, confidence: float) -> None:
        self.raw_text = raw_text
        self.confidence = confidence


class OCRPort(ABC):
    """Port for extracting text from document images."""

    provider: str = "unknown"

    @abstractmethod
    async def extract(self, image_data: bytes, media_type: MediaType) -> OCRResult:
        """Extract text and confidence from the given image data."""
        ...
