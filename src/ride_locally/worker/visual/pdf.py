import io

import fitz  # pymupdf


def is_page_empty(pixmap: fitz.Pixmap, samples_per_check: int = 100) -> bool:
    # Check if page is all white - samples are RGB (3 bytes per pixel)
    samples = pixmap.samples
    n = len(samples) // 3  # number of pixels
    is_empty = all(
        samples[i * 3] == 255
        and samples[i * 3 + 1] == 255
        and samples[i * 3 + 2] == 255
        for i in range(0, n, samples_per_check)
    )
    return is_empty


def prune_empty_pages(pdf_bytes: bytes) -> list[bytes]:
    """Remove empty (all-white) pages from PDF, preserving order."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    kept_pages = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        mat = fitz.Matrix(1, 1)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        if not is_page_empty(pix):
            kept_pages.append(page_num)

    # Extract kept pages into separate PDFs
    results = []
    for page_num in kept_pages:
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        results.append(new_doc.tobytes())

    return results


def pdf_to_jpg(
    pdf_bytes: bytes, zoom: float = 1.5, prune_empty: bool = False
) -> list[bytes]:
    """Convert PDF bytes to JPEG bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("PDF contains no pages")

    results = []
    for page in doc:
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        if prune_empty and is_page_empty(pix):
            continue
        output = io.BytesIO()
        img_data = pix.tobytes("jpg")
        output.write(img_data)
        result_bytes = output.getvalue()
        results.append(result_bytes)

    return results
