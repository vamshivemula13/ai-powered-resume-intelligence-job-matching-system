"""
Domain-Specific Exceptions Hierarchy.

Clean architecture isolates system-specific errors into strongly-typed exceptions
so that API layers and CLI tools can map them to appropriate HTTP codes or exit codes
without leaking internal stack traces or database driver details.
"""

from typing import Any


class AppException(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to structured dictionary format for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class PDFProcessingError(AppException):
    """Raised when PDF extraction, decryption, or layout parsing fails."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            message=message, code="PDF_PROCESSING_ERROR", details=details
        )


class TaxonomyError(AppException):
    """Raised when skill taxonomy file is missing, corrupt, or contains invalid schemas."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message=message, code="TAXONOMY_ERROR", details=details)


class ModelInferenceError(AppException):
    """Raised when NLP or SentenceTransformers embedding inference fails."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            message=message, code="MODEL_INFERENCE_ERROR", details=details
        )


class EntityNotFoundError(AppException):
    """Raised when a requested resource (candidate, resume, job, report) does not exist."""

    def __init__(
        self,
        entity_name: str,
        entity_id: Any,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = details or {}
        merged_details.update({"entity": entity_name, "id": str(entity_id)})
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' was not found.",
            code="ENTITY_NOT_FOUND",
            details=merged_details,
        )


class ValidationError(AppException):
    """Raised when business logic validation fails (e.g., negative experience, bad weights)."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)
