"""
Resume Upload and Parsing API Endpoints.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.dependencies import (
    get_candidate_repo,
    get_pdf_extractor,
    get_resume_parser,
    get_skill_extractor,
)
from app.core.config import settings
from app.core.exceptions import PDFProcessingError
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.resume import ParsedResume
from app.services.pdf_service import BasePDFExtractor
from app.services.resume_parser import ResumeParserService
from app.services.skill_extractor import SkillExtractorService

router = APIRouter(prefix="/resumes", tags=["Resumes"])


class TextResumeInput(BaseModel):
    """Payload for submitting raw text resume content."""

    text: str
    filename: str = "pasted_resume.txt"


@router.post(
    "/upload",
    response_model=ParsedResume,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a candidate PDF resume",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF Resume file"),
    pdf_ext: BasePDFExtractor = Depends(get_pdf_extractor),
    parser: ResumeParserService = Depends(get_resume_parser),
    skill_ext: SkillExtractorService = Depends(get_skill_extractor),
    cand_repo: CandidateRepository = Depends(get_candidate_repo),
) -> ParsedResume:
    """
    Accepts PDF file, validates MIME type and file size, extracts text & layout,
    segments sections, detects skills, and persists Candidate and Resume records.
    """
    # 1. Validate MIME type
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Permitted types: {settings.allowed_mime_types}",
        )

    # 2. Read bytes and check size limit
    content_bytes = await file.read()
    if len(content_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size limit of {settings.max_upload_size_bytes // (1024 * 1024)} MB.",
        )

    # 3. Extract text via PyMuPDF
    try:
        extracted_doc = pdf_ext.extract(content_bytes)
    except PDFProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_dict()) from exc

    # 4. Parse sections and profile
    parsed = parser.parse(extracted_doc, filename=file.filename or "resume.pdf")

    # 5. Persist to database if candidate has an identifier
    contact = parsed.candidate_profile.contact
    cand_name = contact.full_name or file.filename or "Unknown Candidate"

    candidate = None
    if contact.email:
        candidate = await cand_repo.get_by_email(contact.email)

    if candidate is None:
        candidate = Candidate(
            full_name=cand_name,
            email=contact.email,
            phone=contact.phone,
            linkedin_url=contact.linkedin_url,
            github_url=contact.github_url,
            summary=parsed.candidate_profile.summary,
            estimated_experience_years=parsed.candidate_profile.estimated_experience_years,
        )
        await cand_repo.create(candidate)

    # Create Resume entity
    resume_entity = Resume(
        candidate_id=candidate.id,
        filename=parsed.filename,
        total_pages=parsed.total_pages,
        is_scanned=parsed.is_scanned,
        raw_text=parsed.raw_text,
        cleaned_text=parsed.cleaned_text,
        sections_json={k.value: v for k, v in parsed.sections.items()},
    )
    cand_repo.session.add(resume_entity)
    await cand_repo.session.flush()

    return parsed


@router.post(
    "/parse-text",
    response_model=ParsedResume,
    summary="Parse plain-text resume content directly",
)
async def parse_text_resume(
    payload: TextResumeInput,
    parser: ResumeParserService = Depends(get_resume_parser),
) -> ParsedResume:
    """Convenience endpoint to parse raw resume text directly without PDF upload."""
    from app.services.pdf_service import ExtractedDocument

    doc = ExtractedDocument(
        raw_text=payload.text,
        cleaned_text=payload.text.strip(),
        total_pages=1,
        character_count=len(payload.text),
        word_count=len(payload.text.split()),
    )
    return parser.parse(doc, filename=payload.filename)
