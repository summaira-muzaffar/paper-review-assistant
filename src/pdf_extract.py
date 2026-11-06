"""PDF text extraction.

Built in Step 2.

Job: take the raw bytes of an uploaded PDF, open them with
PyMuPDF, and return the text page by page plus one combined text
string. Everything else in the project works from this text, so
this module is kept small and strict: a file that is not a valid
PDF raises an error here, and the interface shows that error
instead of crashing.
"""

import pymupdf


class PdfExtractionError(Exception):
    """Raised when a file cannot be read as a PDF."""


def extract_text_from_bytes(pdf_bytes):
    """Extract text from PDF bytes.

    Args:
        pdf_bytes: the raw bytes of one uploaded PDF file.

    Returns:
        A dictionary with three entries:
        page_count: number of pages in the PDF (int)
        pages: the text of each page, in order (list of str)
        text: all page texts combined into one string, with a
            page marker line before each page, for display

    Raises:
        PdfExtractionError: if the bytes are not a readable PDF.
    """
    if not pdf_bytes:
        raise PdfExtractionError("The uploaded file is empty.")

    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as error:
        raise PdfExtractionError(
            "This file could not be opened as a PDF."
        ) from error

    pages = []
    try:
        for page in document:
            pages.append(page.get_text().strip())
    finally:
        document.close()

    combined_parts = []
    for index, page_text in enumerate(pages, start=1):
        combined_parts.append(f"--- Page {index} ---\n{page_text}")

    return {
        "page_count": len(pages),
        "pages": pages,
        "text": "\n\n".join(combined_parts),
    }
