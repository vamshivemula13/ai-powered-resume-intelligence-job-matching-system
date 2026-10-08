"""
Unit Tests for Matching and Scoring Engine (app/services/matching_service.py).
"""

from app.schemas.job import JobCreate
from app.services.job_parser import job_parser_service
from app.services.matching_service import matching_service
from app.services.pdf_service import ExtractedDocument
from app.services.resume_parser import resume_parser_service


def test_matching_engine_high_compatibility() -> None:
    """Verify strong candidate scores high overall and has strong matches."""
    resume_text = """
David Miller
david@example.com | 555-432-1234
https://linkedin.com/in/davidmiller | https://github.com/davidmiller

PROFESSIONAL SUMMARY
Senior Backend Engineer with 6 years of experience in Python, FastAPI, and PostgreSQL.

SKILLS
Python, FastAPI, PostgreSQL, Docker, AWS, Redis

WORK EXPERIENCE
Senior Developer
2020 - Present
* Built asynchronous microservices with FastAPI and PostgreSQL.
* Deployed containerized applications with Docker to AWS.

EDUCATION
Bachelor of Science in Computer Science
2020
"""
    job_text = """
Python Backend Developer

REQUIRED QUALIFICATIONS
* 4+ years experience in Python and FastAPI.
* Deep knowledge of PostgreSQL.

PREFERRED QUALIFICATIONS
* AWS, Docker, and Redis experience.
"""
    doc = ExtractedDocument(
        raw_text=resume_text,
        cleaned_text=resume_text.strip(),
        total_pages=1,
        character_count=len(resume_text),
        word_count=len(resume_text.split()),
    )
    resume = resume_parser_service.parse(doc)
    job = job_parser_service.parse(JobCreate(title="Python Developer", description=job_text))

    report = matching_service.analyze_match(resume, job)

    assert report.overall_score >= 75.0
    assert report.breakdown.skill_score >= 90.0
    assert report.breakdown.experience_score == 100.0
    assert len(report.missing_critical_skills) == 0
    assert len(report.strengths) >= 2


def test_matching_engine_low_compatibility() -> None:
    """Verify misaligned candidate receives low score and clear missing skills."""
    resume_text = """
Frontend Specialist
frontend@example.com
Specializes in React, CSS, HTML with 1 year of experience.
"""
    job_text = """
Principal Cloud Architect
REQUIRED QUALIFICATIONS
* 8+ years experience.
* AWS, Kubernetes, Terraform, Go, Microservices.
"""
    doc = ExtractedDocument(
        raw_text=resume_text,
        cleaned_text=resume_text.strip(),
        total_pages=1,
        character_count=len(resume_text),
        word_count=len(resume_text.split()),
    )
    resume = resume_parser_service.parse(doc)
    job = job_parser_service.parse(JobCreate(title="Cloud Architect", description=job_text))

    report = matching_service.analyze_match(resume, job)

    assert report.overall_score < 50.0
    assert len(report.missing_critical_skills) >= 2
    assert any("Kubernetes" in s or "AWS" in s or "Go" in s for s in report.missing_critical_skills)


def test_candidate_ranking_order() -> None:
    """Verify multi-candidate ranking places better-aligned candidates higher."""
    job = job_parser_service.parse(
        JobCreate(
            title="FastAPI Engineer",
            description="REQUIRED: Python, FastAPI, PostgreSQL. 3+ years experience.",
        )
    )

    strong_text = "Strong Candidate\nstrong@test.com\nPython, FastAPI, PostgreSQL\n2019 - Present\nBachelor's in CS"
    weak_text = "Junior Dev\njunior@test.com\nHTML, CSS, JavaScript\n2023 - Present"

    doc_strong = ExtractedDocument(
        raw_text=strong_text,
        cleaned_text=strong_text,
        total_pages=1,
        character_count=len(strong_text),
        word_count=len(strong_text.split()),
    )
    doc_weak = ExtractedDocument(
        raw_text=weak_text,
        cleaned_text=weak_text,
        total_pages=1,
        character_count=len(weak_text),
        word_count=len(weak_text.split()),
    )

    res_strong = resume_parser_service.parse(doc_strong)
    res_weak = resume_parser_service.parse(doc_weak)

    ranking = matching_service.rank_candidates([res_weak, res_strong], job)

    assert len(ranking.rankings) == 2
    # Strong candidate should be rank 1
    assert ranking.rankings[0].candidate_name == "Strong Candidate"
    assert ranking.rankings[0].overall_score > ranking.rankings[1].overall_score
