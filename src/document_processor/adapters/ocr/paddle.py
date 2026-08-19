import asyncio
import logging

import numpy as np

from document_processor.core.errors import OCRFailureError, OCRTimeoutError
from document_processor.domain.models.document import MediaType
from document_processor.domain.ports.ocr import OCRPort, OCRResult

logger = logging.getLogger(__name__)


class PaddleOCRAdapter(OCRPort):
    """PaddleOCR-backed adapter for extracting text from document images."""

    async def extract(self, image_data: bytes, media_type: MediaType) -> OCRResult:
        """Extract text and confidence from an image using PaddleOCR."""
        try:
            from PIL import Image

            img = Image.open(__import__("io").BytesIO(image_data))
            img_array = np.array(img.convert("RGB"))

            result = await asyncio.wait_for(
                asyncio.to_thread(self._run_ocr, img_array),
                timeout=60,
            )

            if result is None:
                raise OCRFailureError("PaddleOCR returned no text")

            return result

        except TimeoutError as e:
            raise OCRTimeoutError() from e
        except Exception as e:
            logger.exception("PaddleOCR error")
            raise OCRFailureError(str(e)) from e

    @staticmethod
    def _run_ocr(img_array: np.ndarray) -> OCRResult | None:
        from paddleocr import PaddleOCR  # type: ignore[import-untyped]  # ADR-011

        ocr = PaddleOCR(lang="es", use_angle_cls=True)
        results = ocr.ocr(img_array)

        if not results or not results[0]:
            return OCRResult(raw_text="", confidence=0.0)

        texts = []
        confidences = []
        for line in results[0]:
            text = line[1][0]
            conf = line[1][1]
            texts.append(text)
            confidences.append(conf)

        combined_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(raw_text=combined_text, confidence=avg_confidence)
