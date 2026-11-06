"""Tests for Step 2, PDF text extraction.

Run directly with python, or with pytest if it is installed:

    .venv/bin/python tests/test_pdf_extract.py

The test builds a small real PDF in memory with PyMuPDF, with
known text on two pages, then checks that the extraction module
returns that text, the right page count, and clean errors for
bad input. No sample file is needed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pymupdf

from src.pdf_extract import PdfExtractionError, extract_text_from_bytes

PAGE_ONE_TEXT = "Automated Review of Academic Papers"
PAGE_TWO_TEXT = "This paragraph discusses the method and its results."


def make_test_pdf_bytes():
    document = pymupdf.open()
    page_one = document.new_page()
    page_one.insert_text((72, 72), PAGE_ONE_TEXT)
    page_two = document.new_page()
    page_two.insert_text((72, 72), PAGE_TWO_TEXT)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_extracts_text_from_two_pages():
    result = extract_text_from_bytes(make_test_pdf_bytes())
    assert result["page_count"] == 2
    assert PAGE_ONE_TEXT in result["pages"][0]
    assert PAGE_TWO_TEXT in result["pages"][1]
    assert PAGE_ONE_TEXT in result["text"]
    assert "--- Page 2 ---" in result["text"]


def test_invalid_bytes_raise_clean_error():
    try:
        extract_text_from_bytes(b"this is not a pdf")
    except PdfExtractionError:
        return
    raise AssertionError("Invalid bytes should raise PdfExtractionError")


def test_empty_bytes_raise_clean_error():
    try:
        extract_text_from_bytes(b"")
    except PdfExtractionError:
        return
    raise AssertionError("Empty bytes should raise PdfExtractionError")


if __name__ == "__main__":
    test_extracts_text_from_two_pages()
    test_invalid_bytes_raise_clean_error()
    test_empty_bytes_raise_clean_error()
    print("TEST_PDF_EXTRACT_OK 3 tests passed")
