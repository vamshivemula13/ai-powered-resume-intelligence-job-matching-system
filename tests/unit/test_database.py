"""
Unit Tests for Database Models and Repositories (app/repositories/).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - Register all models with Base
from app.models.base import Base
from app.models.candidate import Candidate
from app.models.job import Job
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.job_repository import JobRepository


@pytest.fixture
async def async_test_session():
    """In-memory SQLite async engine fixture for isolated repository testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_candidate_repository_crud(async_test_session: AsyncSession) -> None:
    """Verify Candidate entity creation, retrieval by ID, and lookup by email."""
    repo = CandidateRepository(async_test_session)

    new_cand = Candidate(
        full_name="Bruce Wayne",
        email="bruce@wayne.corp",
        phone="+1 555-019-2834",
        estimated_experience_years=10.0,
    )
    created = await repo.create(new_cand)
    assert created.id is not None
    assert created.full_name == "Bruce Wayne"

    fetched = await repo.get_by_email("bruce@wayne.corp")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.estimated_experience_years == 10.0


@pytest.mark.asyncio
async def test_job_repository_crud(async_test_session: AsyncSession) -> None:
    """Verify Job entity creation, listing, and ID query."""
    repo = JobRepository(async_test_session)

    job = Job(
        title="Lead Cloud Architect",
        company="Gotham Tech",
        description="Design distributed microservices on AWS and Kubernetes.",
        min_experience_years=7.0,
        min_education_level="Bachelor's",
    )
    created = await repo.create(job)
    assert created.id is not None

    all_jobs = await repo.get_all()
    assert len(all_jobs) == 1
    assert all_jobs[0].title == "Lead Cloud Architect"
