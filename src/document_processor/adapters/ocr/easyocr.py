import asyncio
import logging

from document_processor.core.errors import OCRFailureError, OCRTimeoutError
from document_processor.domain.models.document import MediaType
from document_processor.domain.ports.ocr import OCRPort, OCRResult

logger = logging.getLogger(__name__)


class EasyOCRAdapter(OCRPort):
    """EasyOCR-backed adapter for extracting text from document images."""

    async def extract(self, image_data: bytes, media_type: MediaType) -> OCRResult:
        """Extract text and confidence from an image using EasyOCR."""
        try:
            import numpy as np
            from PIL import Image

            img = Image.open(__import__("io").BytesIO(image_data))
            img_array = np.array(img.convert("RGB"))

            result = await asyncio.wait_for(
                asyncio.to_thread(self._run_ocr, img_array),
                timeout=60,
            )

            if result is None:
                raise OCRFailureError("EasyOCR returned no text")

            return result

        except TimeoutError as e:
            raise OCRTimeoutError() from e
        except Exception as e:
            logger.exception("EasyOCR error")
            raise OCRFailureError(str(e)) from e

    @staticmethod
    def _run_ocr(img_array) -> OCRResult | None:
        import easyocr

        reader = easyocr.Reader(["es"])
        results = reader.readtext(img_array)

        if not results:
            return OCRResult(raw_text="", confidence=0.0)

        texts = []
        confidences = []
        for _bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)

        combined_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(raw_text=combined_text, confidence=avg_confidence)
