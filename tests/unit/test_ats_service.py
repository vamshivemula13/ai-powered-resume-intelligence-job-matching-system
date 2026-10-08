"""
Unit Tests for ATS Compliance Analyzer (app/services/ats_service.py).
"""

from app.schemas.candidate import CandidateProfile, ContactInfo
from app.schemas.resume import ParsedResume, ResumeSectionType
from app.services.ats_service import ats_service


def test_ats_analyzer_perfect_score() -> None:
    """Verify resume with all contact and structural elements receives high ATS score."""
    profile = CandidateProfile(
        contact=ContactInfo(
            full_name="Sarah Connor",
            email="sarah@resistance.org",
            phone="+1 555-987-6543",
            linkedin_url="https://linkedin.com/in/sarahconnor",
            github_url="https://github.com/sarahconnor",
        ),
        summary="Experienced engineering lead with a focus on resilient software architectures.",
    )
    long_experience = "Led backend infrastructure teams for 6 years across distributed systems. " * 10
    resume = ParsedResume(
        filename="sarah_connor.pdf",
        total_pages=1,
        is_scanned=False,
        candidate_profile=profile,
        sections={
            ResumeSectionType.SUMMARY: "Experienced engineering lead.",
            ResumeSectionType.EXPERIENCE: long_experience,
            ResumeSectionType.SKILLS: "Python, FastAPI, Docker, Kubernetes, PostgreSQL",
            ResumeSectionType.EDUCATION: "B.S. in Computer Science, 2018",
        },
        cleaned_text=f"Sarah Connor\n{long_experience}\nPython, FastAPI, Docker",
    )

    report = ats_service.analyze(resume)
    assert report.ats_score >= 90.0
    assert len(report.passed_checks) >= 7
    assert any("Candidate name detected" in c for c in report.passed_checks)


def test_ats_analyzer_penalizes_missing_contact() -> None:
    """Verify resume lacking phone and email receives lower ATS score and clear improvement advice."""
    profile = CandidateProfile(
        contact=ContactInfo(full_name=None, email=None, phone=None),
    )
    resume = ParsedResume(
        filename="sparse.pdf",
        total_pages=1,
        is_scanned=False,
        candidate_profile=profile,
        sections={},
        cleaned_text="Short content with missing information.",
    )

    report = ats_service.analyze(resume)
    assert report.ats_score < 50.0
    assert len(report.improvements) >= 3
    assert any("email" in imp.lower() for imp in report.improvements)
    assert any("phone" in imp.lower() for imp in report.improvements)
