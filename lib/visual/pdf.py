import io

import fitz  # pymupdf


def pdf_to_jpg(pdf_bytes: bytes, zoom: float = 1.5) -> bytes:
    """Convert PDF bytes to JPEG bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("PDF contains no pages")

    page = doc[0]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    output = io.BytesIO()
    img_data = pix.tobytes("jpg")
    output.write(img_data)
    return output.getvalue()
