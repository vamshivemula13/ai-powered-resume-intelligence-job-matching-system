"""
Integration Tests for FastAPI REST Endpoints (app/main.py).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_index_endpoint() -> None:
    """Verify GET / returns system overview and operational status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["docs_url"] == "/docs"


@pytest.mark.asyncio
async def test_health_check_endpoint() -> None:
    """Verify GET /api/v1/health returns database and taxonomy health metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["taxonomy"]["rules_count"] > 10


@pytest.mark.asyncio
async def test_parse_text_resume_endpoint() -> None:
    """Verify POST /api/v1/resumes/parse-text extracts contact details and sections."""
    transport = ASGITransport(app=app)
    payload = {
        "text": (
            "Alice Walker\n"
            "alice@walker.org | +1 555-123-4567\n"
            "SKILLS\nPython, FastAPI, Docker\n"
            "EXPERIENCE\n2021 - Present\nBackend Developer at Acme Corp"
        ),
        "filename": "alice.txt",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/resumes/parse-text", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["candidate_profile"]["contact"]["full_name"] == "Alice Walker"
        assert data["candidate_profile"]["contact"]["email"] == "alice@walker.org"


@pytest.mark.asyncio
async def test_create_and_parse_job_endpoint() -> None:
    """Verify POST /api/v1/jobs decomposes requirements and returns structured job."""
    transport = ASGITransport(app=app)
    payload = {
        "title": "Backend Software Engineer",
        "description": (
            "We are hiring a backend engineer.\n"
            "REQUIRED QUALIFICATIONS\n"
            "* 3+ years experience in Python and FastAPI.\n"
            "* PostgreSQL database knowledge.\n"
            "PREFERRED QUALIFICATIONS\n"
            "* Docker and Redis."
        ),
        "company": "Tech Innovations Inc.",
        "location": "Remote",
        "is_remote": True,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Backend Software Engineer"
        assert "Python" in data["requirements"]["required_skills"]
        assert "FastAPI" in data["requirements"]["required_skills"]
        assert data["requirements"]["min_experience_years"] == 3.0


@pytest.mark.asyncio
async def test_direct_match_analysis_endpoint() -> None:
    """Verify POST /api/v1/matching/analyze returns match report, breakdown, and ATS score."""
    transport = ASGITransport(app=app)
    payload = {
        "candidate_name": "Bob Stone",
        "resume_text": (
            "Bob Stone\n"
            "bob@stone.dev\n"
            "SKILLS\nPython, FastAPI, PostgreSQL\n"
            "EXPERIENCE\n4 years backend experience with FastAPI and PostgreSQL."
        ),
        "job_title": "FastAPI Developer",
        "job_text": "REQUIRED: Python, FastAPI, PostgreSQL. 3+ years experience.",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/matching/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["candidate_name"] == "Bob Stone"
        assert data["overall_score"] >= 70.0
        assert "breakdown" in data
        assert "ats_analysis" in data
        assert "skill_gap" in data


@pytest.mark.asyncio
async def test_direct_candidate_ranking_endpoint() -> None:
    """Verify POST /api/v1/matching/rank returns sorted leaderboard."""
    transport = ASGITransport(app=app)
    payload = {
        "job_title": "Python Specialist",
        "job_description": "REQUIRED: Python, FastAPI. 2+ years experience.",
        "resumes": [
            {
                "name": "Candidate A",
                "resume_text": "Candidate A\nPython, FastAPI expert with 4 years experience.",
            },
            {
                "name": "Candidate B",
                "resume_text": "Candidate B\nFrontend dev skilled in HTML and CSS.",
            },
        ],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/matching/rank", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_candidates"] == 2
        assert len(data["rankings"]) == 2
        # Candidate A should be top rank
        assert data["rankings"][0]["candidate_name"] == "Candidate A"
        assert data["rankings"][0]["rank"] == 1
