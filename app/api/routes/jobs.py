"""
Job Postings and Analysis API Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_job_parser, get_job_repo
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate, JobParsed
from app.services.job_parser import JobParserService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobParsed,
    status_code=status.HTTP_201_CREATED,
    summary="Create and analyze a new job description",
)
async def create_job(
    job_in: JobCreate,
    parser: JobParserService = Depends(get_job_parser),
    job_repo: JobRepository = Depends(get_job_repo),
) -> JobParsed:
    """
    Ingests job description, extracts required/preferred competencies,
    computes experience/education requirements, and persists Job record.
    """
    parsed = parser.parse(job_in)

    job_entity = Job(
        title=parsed.title,
        company=parsed.company,
        location=parsed.location,
        is_remote=parsed.is_remote,
        description=parsed.cleaned_description,
        min_experience_years=parsed.requirements.min_experience_years,
        min_education_level=parsed.requirements.min_education_level,
        responsibilities_json=parsed.requirements.responsibilities,
    )
    await job_repo.create(job_entity)

    return parsed


@router.get(
    "",
    summary="List all jobs",
)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Retrieves paginated list of created job postings."""
    jobs = await job_repo.get_all(skip=skip, limit=limit)
    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "is_remote": j.is_remote,
            "min_experience_years": j.min_experience_years,
            "min_education_level": j.min_education_level,
            "created_at": j.created_at,
        }
        for j in jobs
    ]


@router.get(
    "/{job_id}",
    summary="Get job description details by ID",
)
async def get_job_by_id(
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repo),
    parser: JobParserService = Depends(get_job_parser),
) -> JobParsed:
    """Fetches job by ID and returns parsed requirements."""
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    job_input = JobCreate(
        title=job.title,
        description=job.description,
        company=job.company,
        location=job.location,
        is_remote=job.is_remote,
    )
    return parser.parse(job_input)
