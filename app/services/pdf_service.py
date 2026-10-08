"""
PDF Extraction Service Module.

Provides document extraction using PyMuPDF (fitz) with clean layout preservation,
text sanitization, and an extensible architecture for future OCR plugins.
"""

import io
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from app.core.exceptions import PDFProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentBlock:
    """Represents an atomic text block extracted from a document page."""

    text: str
    page_number: int
    block_number: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)


@dataclass
class ExtractedDocument:
    """Structured container holding extracted document text and metadata."""

    raw_text: str
    cleaned_text: str
    total_pages: int
    character_count: int
    word_count: int
    blocks: list[DocumentBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_scanned: bool = False

    @property
    def is_empty(self) -> bool:
        """Indicates if the document contained zero readable characters."""
        return len(self.cleaned_text.strip()) == 0


class BasePDFExtractor(ABC):
    """
    Abstract Base Class (Interface) for PDF extraction.
    Follows the Dependency Inversion Principle so alternative extraction engines
    (e.g., Tesseract OCR, AWS Textract) can be swapped without altering business logic.
    """

    @abstractmethod
    def extract(self, source: bytes | Path | str) -> ExtractedDocument:
        """Extract text and metadata from bytes, a file path, or stream."""
        pass


class TextSanitizer:
    """
    Handles string normalization, removing artifacts common in PDF text streams
    such as broken hyphenation, excessive whitespace, and incompatible bullet symbols.
    """

    # Common unicode bullets mapped to standard ASCII asterisks
    BULLET_PATTERN = re.compile(r"[\u2022\u2023\u25E6\u2043\u2219\u25CF\u25CB\u25A0\u25AA]")
    # Linebreak hyphenation (e.g., 'archi-\ntecture' -> 'architecture')
    HYPHENATION_PATTERN = re.compile(r"(\w+)-\n\s*(\w+)")
    # Multiple consecutive whitespace (excluding newlines)
    MULTI_SPACE_PATTERN = re.compile(r"[^\S\r\n]+")
    # Excessive empty lines (more than two consecutive newlines)
    EXCESSIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")

    @classmethod
    def clean(cls, text: str) -> str:
        """Apply sequential sanitization steps to raw text."""
        if not text:
            return ""

        # Step 1: Normalize unicode bullets
        cleaned = cls.BULLET_PATTERN.sub("* ", text)

        # Step 2: Fix word hyphenation split across lines
        cleaned = cls.HYPHENATION_PATTERN.sub(r"\1\2", cleaned)

        # Step 3: Replace weird control characters (keep \n, \r, \t)
        cleaned = "".join(char for char in cleaned if char.isprintable() or char in "\n\r\t")

        # Step 4: Condense horizontal whitespace
        cleaned = cls.MULTI_SPACE_PATTERN.sub(" ", cleaned)

        # Step 5: Condense excessive blank lines
        cleaned = cls.EXCESSIVE_NEWLINES_PATTERN.sub("\n\n", cleaned)

        return cleaned.strip()


class PyMuPDFExtractor(BasePDFExtractor):
    """
    High-performance C-backed PDF text extractor using PyMuPDF (fitz).
    Preserves text block coordinates and detects image-only/scanned documents.
    """

    # Minimum character threshold under which a document is considered scanned/image-only
    SCANNED_CHARACTER_THRESHOLD = 50

    def extract(self, source: bytes | Path | str) -> ExtractedDocument:
        """
        Extract text, structure, and metadata from a PDF source.

        Args:
            source: Raw PDF bytes, a Path object, or a filepath string.

        Returns:
            ExtractedDocument containing sanitized text and block telemetry.

        Raises:
            PDFProcessingError: If the file is invalid, corrupt, encrypted, or unreadable.
        """
        doc: fitz.Document | None = None
        try:
            if isinstance(source, bytes):
                if len(source) == 0:
                    raise PDFProcessingError(
                        message="Cannot process empty PDF: byte payload is 0 bytes.",
                        details={"reason": "EMPTY_PAYLOAD"},
                    )
                doc = fitz.open(stream=io.BytesIO(source), filetype="pdf")
            else:
                path = Path(source)
                if not path.exists():
                    raise PDFProcessingError(
                        message=f"PDF file does not exist: {path}",
                        details={"path": str(path)},
                    )
                if path.stat().st_size == 0:
                    raise PDFProcessingError(
                        message=f"PDF file is empty (0 bytes): {path}",
                        details={"path": str(path)},
                    )
                doc = fitz.open(str(path))

            if doc.is_encrypted:
                raise PDFProcessingError(
                    message="PDF is password-protected or encrypted. Please upload an unprotected file.",
                    details={"encrypted": True},
                )

            total_pages = doc.page_count
            if total_pages == 0:
                raise PDFProcessingError(
                    message="PDF document contains zero pages.",
                    details={"total_pages": 0},
                )

            raw_text_parts: list[str] = []
            blocks: list[DocumentBlock] = []

            for page_index in range(total_pages):
                page = doc[page_index]
                page_text = page.get_text("text")
                raw_text_parts.append(page_text)

                # Extract geometric text blocks for fine-grained section analysis
                # page.get_text("blocks") returns tuples: (x0, y0, x1, y1, text, block_no, block_type)
                page_blocks = page.get_text("blocks")
                for block in page_blocks:
                    # block[6] == 0 indicates a text block (1 indicates image block)
                    if len(block) >= 7 and block[6] == 0:
                        block_text = block[4].strip()
                        if block_text:
                            blocks.append(
                                DocumentBlock(
                                    text=block_text,
                                    page_number=page_index + 1,
                                    block_number=block[5],
                                    bbox=(block[0], block[1], block[2], block[3]),
                                )
                            )

            raw_text = "\n\n".join(raw_text_parts)
            cleaned_text = TextSanitizer.clean(raw_text)
            char_count = len(cleaned_text)
            word_count = len(cleaned_text.split())

            # Detect whether document is likely scanned / image-only
            is_scanned = char_count < (self.SCANNED_CHARACTER_THRESHOLD * total_pages)

            metadata = dict(doc.metadata) if doc.metadata else {}
            metadata["page_count"] = total_pages

            logger.info(
                "PDF extracted successfully. Pages: %d, Words: %d, Scanned: %s",
                total_pages,
                word_count,
                is_scanned,
            )

            return ExtractedDocument(
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                total_pages=total_pages,
                character_count=char_count,
                word_count=word_count,
                blocks=blocks,
                metadata=metadata,
                is_scanned=is_scanned,
            )

        except fitz.FileDataError as exc:
            logger.error("PyMuPDF corrupt file error: %s", exc)
            raise PDFProcessingError(
                message="Corrupted or invalid PDF structure.",
                details={"original_error": str(exc)},
            ) from exc
        except PDFProcessingError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error during PDF extraction: %s", exc)
            raise PDFProcessingError(
                message=f"Failed to process PDF: {exc!s}",
                details={"original_error": str(exc)},
            ) from exc
        finally:
            if doc is not None:
                doc.close()


# Default singleton instance for direct application consumption
pdf_extractor = PyMuPDFExtractor()
