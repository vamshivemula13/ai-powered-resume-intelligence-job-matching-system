"""
Unit Tests for Job Description Parser (app/services/job_parser.py).
"""

from app.schemas.job import JobCreate
from app.services.job_parser import job_parser_service

SAMPLE_JOB_DESCRIPTION = """
We are looking for a Senior Python Backend Engineer to join our high-growth platform engineering team.

RESPONSIBILITIES
* Design and implement high-performance asynchronous REST APIs and microservices.
* Optimize database queries, schemas, and connection pools for mission-critical services.
* Collaborate with frontend and DevOps engineers to ship reliable software.

REQUIRED QUALIFICATIONS
* 4+ years of professional experience with Python backend development.
* Strong hands-on proficiency with FastAPI or Django.
* Deep knowledge of relational databases, specifically PostgreSQL.
* Experience designing REST APIs and microservice architectures.
* Bachelor's degree in Computer Science, Software Engineering, or equivalent experience.

PREFERRED QUALIFICATIONS
* Hands-on experience with Docker containerization and Kubernetes orchestration.
* Cloud experience with AWS or GCP.
* Experience using Redis for caching and session management.
* Familiarity with CI/CD pipelines and GitHub Actions.
"""


def test_job_parser_with_required_and_preferred_sections() -> None:
    """Verify clean separation of required vs. preferred skills and qualifications."""
    job_input = JobCreate(
        title="Senior Python Backend Engineer",
        description=SAMPLE_JOB_DESCRIPTION,
        company="Acme Cloud Systems",
        location="San Francisco, CA",
        is_remote=True,
    )

    parsed = job_parser_service.parse(job_input)

    reqs = parsed.requirements

    # Required skills verification
    assert "Python" in reqs.required_skills
    assert "FastAPI" in reqs.required_skills
    assert "PostgreSQL" in reqs.required_skills
    assert "REST API" in reqs.required_skills

    # Preferred skills verification
    assert "Docker" in reqs.preferred_skills
    assert "Kubernetes" in reqs.preferred_skills
    assert "AWS" in reqs.preferred_skills
    assert "Redis" in reqs.preferred_skills

    # Mutual exclusivity
    assert set(reqs.required_skills).isdisjoint(set(reqs.preferred_skills))

    # Experience and education extraction
    assert reqs.min_experience_years == 4.0
    assert reqs.min_education_level == "Bachelor's"

    # Responsibilities extraction
    assert len(reqs.responsibilities) >= 2
    assert any("microservices" in r.lower() for r in reqs.responsibilities)


def test_job_parser_unsegmented_fallback() -> None:
    """Verify parser behaves gracefully on unformatted, single-block job descriptions."""
    text = (
        "Seeking a Python developer with at least 2 years of professional experience. "
        "Must be proficient in Django, PostgreSQL, and Git version control."
    )
    job_input = JobCreate(
        title="Python Developer",
        description=text,
    )

    parsed = job_parser_service.parse(job_input)
    reqs = parsed.requirements

    assert reqs.min_experience_years == 2.0
    assert "Python" in reqs.required_skills
    assert "Django" in reqs.required_skills
    assert "PostgreSQL" in reqs.required_skills
    assert "Git" in reqs.required_skills


def test_job_education_hierarchy_picks_minimum_bar() -> None:
    """Verify that when 'Bachelor's or Master's' is mentioned, Bachelor's is picked as the minimum bar."""
    text = (
        "Requires 3+ years of experience with Python and SQL. "
        "Candidates must hold a Bachelor's or Master's degree in Computer Science."
    )
    job_input = JobCreate(title="Data Engineer", description=text)
    parsed = job_parser_service.parse(job_input)

    assert parsed.requirements.min_education_level == "Bachelor's"
