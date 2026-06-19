from abc import ABC, abstractmethod

from document_processor.domain.models.document import MediaType


class OCRResult:
    def __init__(self, raw_text: str, confidence: float) -> None:
        self.raw_text = raw_text
        self.confidence = confidence


class OCRPort(ABC):
    @abstractmethod
    async def extract(
        self, image_data: bytes, media_type: MediaType
    ) -> OCRResult:
        ...
