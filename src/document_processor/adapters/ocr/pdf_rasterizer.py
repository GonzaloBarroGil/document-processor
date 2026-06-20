from io import BytesIO

from pdf2image import convert_from_bytes
from PIL import Image


async def rasterize_pdf(image_data: bytes) -> bytes:
    pages = convert_from_bytes(image_data, dpi=300)
    if len(pages) == 1:
        output = BytesIO()
        pages[0].save(output, format="PNG")
        return output.getvalue()

    widths, heights = zip(*(p.size for p in pages), strict=False)
    total_height = sum(heights)
    max_width = max(widths)

    merged = Image.new("RGB", (max_width, total_height), color=(255, 255, 255))
    y_offset = 0
    for page in pages:
        merged.paste(page, (0, y_offset))
        y_offset += page.height

    output = BytesIO()
    merged.save(output, format="PNG")
    return output.getvalue()
