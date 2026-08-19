from document_processor.domain.models.document import MediaType


class PreprocessOutput:
    """The image bytes and media type produced by the preprocess step."""

    def __init__(self, image_data: bytes, media_type: MediaType) -> None:
        self.image_data = image_data
        self.media_type = media_type


async def preprocess(image_data: bytes, media_type: MediaType) -> PreprocessOutput:
    """Transcode or rasterize an image into a form OCR can consume."""
    if media_type in (MediaType.JPEG, MediaType.PNG):
        return PreprocessOutput(image_data=image_data, media_type=media_type)

    if media_type == MediaType.HEIC:
        from document_processor.adapters.ocr.heic_transcoder import (
            transcode_heic,
        )

        transcoded = await transcode_heic(image_data)
        return PreprocessOutput(image_data=transcoded, media_type=MediaType.PNG)

    if media_type == MediaType.PDF:
        from document_processor.adapters.ocr.pdf_rasterizer import (
            rasterize_pdf,
        )

        rasterized = await rasterize_pdf(image_data)
        return PreprocessOutput(image_data=rasterized, media_type=MediaType.PNG)

    return PreprocessOutput(image_data=image_data, media_type=media_type)
