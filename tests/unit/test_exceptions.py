"""
Unit Tests for Domain Exceptions (app/core/exceptions.py).
"""

from app.core.exceptions import (
    AppException,
    EntityNotFoundError,
    PDFProcessingError,
)


def test_base_app_exception_structure() -> None:
    """Verify AppException serialization to standardized dictionary."""
    exc = AppException(
        message="A system fault occurred",
        code="CUSTOM_CODE",
        details={"reason": "test"},
    )
    result = exc.to_dict()
    assert result["error"]["code"] == "CUSTOM_CODE"
    assert result["error"]["message"] == "A system fault occurred"
    assert result["error"]["details"]["reason"] == "test"


def test_entity_not_found_exception() -> None:
    """Verify EntityNotFoundError automatically includes entity name and ID."""
    exc = EntityNotFoundError(entity_name="Resume", entity_id=42)
    result = exc.to_dict()
    assert exc.code == "ENTITY_NOT_FOUND"
    assert "Resume with identifier '42' was not found" in exc.message
    assert result["error"]["details"]["entity"] == "Resume"
    assert result["error"]["details"]["id"] == "42"


def test_pdf_processing_exception() -> None:
    """Verify PDFProcessingError has code PDF_PROCESSING_ERROR."""
    exc = PDFProcessingError("Corrupted stream")
    assert exc.code == "PDF_PROCESSING_ERROR"
