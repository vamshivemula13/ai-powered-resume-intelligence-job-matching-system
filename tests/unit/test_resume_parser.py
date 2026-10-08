"""
Unit Tests for Resume Parser Service (app/services/resume_parser.py).
"""

from app.schemas.resume import ResumeSectionType
from app.services.pdf_service import ExtractedDocument
from app.services.resume_parser import resume_parser_service

SAMPLE_RESUME_TEXT = """
Alex Mercer
alex.mercer@example.com | +1 555-234-5678
https://linkedin.com/in/alex-mercer | https://github.com/alexmercer

PROFESSIONAL SUMMARY
Senior Software Engineer with 6+ years of experience specializing in distributed Python backend architectures, FastAPI microservices, and PostgreSQL database performance tuning.

TECHNICAL SKILLS
Python, FastAPI, Django, PostgreSQL, Docker, Kubernetes, AWS, Redis, Git

WORK EXPERIENCE
Senior Backend Engineer | Acme Tech
2021 - Present
* Architected asynchronous FastAPI microservices serving 10M daily requests.
* Reduced database query latency by 45% using PostgreSQL indexing and Redis caching.

Software Engineer | Globex Corp
2018 - 2021
* Built RESTful APIs using Python and Flask.
* Containerized legacy services with Docker and implemented CI/CD pipelines.

EDUCATION
Bachelor of Science in Computer Science
State University | 2018
"""


def test_resume_parser_full_extraction() -> None:
    """Verify end-to-end extraction of candidate contact, sections, and experience."""
    doc = ExtractedDocument(
        raw_text=SAMPLE_RESUME_TEXT,
        cleaned_text=SAMPLE_RESUME_TEXT.strip(),
        total_pages=1,
        character_count=len(SAMPLE_RESUME_TEXT),
        word_count=len(SAMPLE_RESUME_TEXT.split()),
    )

    parsed = resume_parser_service.parse(doc, filename="alex_mercer.pdf")

    # Verify contact info
    contact = parsed.candidate_profile.contact
    assert contact.full_name == "Alex Mercer"
    assert contact.email == "alex.mercer@example.com"
    assert contact.phone is not None and "555-234-5678" in contact.phone
    assert contact.linkedin_url == "https://linkedin.com/in/alex-mercer"
    assert contact.github_url == "https://github.com/alexmercer"

    # Verify section segmentation
    assert ResumeSectionType.SUMMARY in parsed.sections
    assert ResumeSectionType.SKILLS in parsed.sections
    assert ResumeSectionType.EXPERIENCE in parsed.sections
    assert ResumeSectionType.EDUCATION in parsed.sections

    # Verify content in sections
    assert "FastAPI" in parsed.sections[ResumeSectionType.SKILLS]
    assert "Acme Tech" in parsed.sections[ResumeSectionType.EXPERIENCE]

    # Verify experience calculation (2018-2021 is 3 yrs + 2021-present is >= 3 yrs)
    assert parsed.candidate_profile.estimated_experience_years >= 5.0

    # Verify education entry
    edu_entries = parsed.candidate_profile.education_entries
    assert len(edu_entries) >= 1
    assert edu_entries[0].degree == "Bachelor's"
    assert edu_entries[0].year == 2018


def test_irregular_section_headers() -> None:
    """Verify parser recognizes alternative headers like 'WORK HISTORY' and 'CORE COMPETENCIES'."""
    text = """
Jane Smith
jane@test.org

CORE COMPETENCIES
Python, Go, AWS

WORK HISTORY:
2020 - 2023
Software Developer at Cloud Inc.

ACADEMIC BACKGROUND
Master of Science in Software Engineering
2020
"""
    doc = ExtractedDocument(
        raw_text=text,
        cleaned_text=text.strip(),
        total_pages=1,
        character_count=len(text),
        word_count=len(text.split()),
    )
    parsed = resume_parser_service.parse(doc)

    assert ResumeSectionType.SKILLS in parsed.sections
    assert ResumeSectionType.EXPERIENCE in parsed.sections
    assert ResumeSectionType.EDUCATION in parsed.sections

    edu_entries = parsed.candidate_profile.education_entries
    assert any(e.degree == "Master's" for e in edu_entries)


def test_resume_with_minimal_structure() -> None:
    """Verify fallback handling when a resume has no formal section headers."""
    unstructured_text = "Alice Cooper\nalice@example.com\nJust a software developer with 4 years of experience."
    doc = ExtractedDocument(
        raw_text=unstructured_text,
        cleaned_text=unstructured_text,
        total_pages=1,
        character_count=len(unstructured_text),
        word_count=len(unstructured_text.split()),
    )
    parsed = resume_parser_service.parse(doc)

    assert parsed.candidate_profile.contact.full_name == "Alice Cooper"
    assert parsed.candidate_profile.contact.email == "alice@example.com"
    assert parsed.candidate_profile.estimated_experience_years == 4.0
