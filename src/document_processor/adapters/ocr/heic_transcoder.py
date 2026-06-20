from io import BytesIO

from document_processor.core.errors import HeicTranscodingError


async def transcode_heic(image_data: bytes) -> bytes:
    try:
        import numpy as np
        from PIL import Image
        from pillow_heif import register_heif_opener

        register_heif_opener()

        img = Image.open(BytesIO(image_data))
        output = BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

    except Exception as e:
        raise HeicTranscodingError(str(e)) from e
