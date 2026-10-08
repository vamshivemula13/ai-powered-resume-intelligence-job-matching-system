"""
Unit Tests for PDF Extraction Service (app/services/pdf_service.py).
"""

import io

import fitz
import pytest

from app.core.exceptions import PDFProcessingError
from app.services.pdf_service import (
    TextSanitizer,
    pdf_extractor,
)


def create_sample_pdf(text: str, num_pages: int = 1) -> bytes:
    """Helper utility to generate in-memory synthetic PDF bytes for testing."""
    doc = fitz.open()
    for _ in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 72), text)
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    return stream.getvalue()


def test_extract_valid_pdf_bytes() -> None:
    """Verify clean extraction of text, page count, and block coordinates."""
    content = "John Doe\nSenior Python Backend Engineer\nSkills: FastAPI, PostgreSQL, Docker"
    pdf_bytes = create_sample_pdf(content, num_pages=2)

    extracted = pdf_extractor.extract(pdf_bytes)

    assert extracted.total_pages == 2
    assert "John Doe" in extracted.cleaned_text
    assert "FastAPI" in extracted.cleaned_text
    assert extracted.word_count > 5
    assert len(extracted.blocks) > 0
    assert extracted.is_scanned is False


def test_empty_bytes_raises_pdf_processing_error() -> None:
    """Verify that empty 0-byte input raises PDFProcessingError."""
    with pytest.raises(PDFProcessingError) as exc_info:
        pdf_extractor.extract(b"")

    assert exc_info.value.code == "PDF_PROCESSING_ERROR"
    assert "empty pdf" in exc_info.value.message.lower()


def test_corrupt_bytes_raises_pdf_processing_error() -> None:
    """Verify that corrupt byte streams raise a structured PDFProcessingError."""
    corrupted_data = b"%PDF-1.4\nthis-is-corrupted-binary-garbage-not-valid-pdf"
    with pytest.raises(PDFProcessingError) as exc_info:
        pdf_extractor.extract(corrupted_data)

    assert exc_info.value.code == "PDF_PROCESSING_ERROR"


def test_text_sanitizer_normalizes_bullets_and_hyphens() -> None:
    """Verify TextSanitizer handles unicode bullets, split hyphenation, and whitespace."""
    dirty_text = "• Developed micro-\nservices for high-traffic apps.\n\n\n\n  ● Managed cloud."
    cleaned = TextSanitizer.clean(dirty_text)

    # Bullet points should become standardized asterisk
    assert "* Developed" in cleaned
    # Hyphenation split across line should be joined
    assert "microservices" in cleaned
    # Excessive blank lines condensed
    assert "\n\n\n\n" not in cleaned


def test_scanned_pdf_heuristic_detection() -> None:
    """Verify that documents with sparse text are marked as is_scanned=True."""
    minimal_text = "A"  # Under the 50 char threshold
    pdf_bytes = create_sample_pdf(minimal_text, num_pages=1)

    extracted = pdf_extractor.extract(pdf_bytes)
    assert extracted.is_scanned is True


def test_nonexistent_file_path_raises_error(tmp_path) -> None:
    """Verify that pointing to a nonexistent path raises PDFProcessingError."""
    missing_file = tmp_path / "nonexistent.pdf"
    with pytest.raises(PDFProcessingError) as exc_info:
        pdf_extractor.extract(missing_file)

    assert "does not exist" in exc_info.value.message
