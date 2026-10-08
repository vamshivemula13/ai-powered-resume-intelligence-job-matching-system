"""
Candidate Matching and Ranking API Endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_job_parser,
    get_matching_service,
    get_resume_parser,
)
from app.schemas.job import JobCreate
from app.schemas.match import CandidateRankingResponse, MatchAnalysisReport
from app.services.job_parser import JobParserService
from app.services.matching_service import MatchingEngineService
from app.services.pdf_service import ExtractedDocument
from app.services.resume_parser import ResumeParserService

router = APIRouter(prefix="/matching", tags=["Matching"])


class DirectMatchRequest(BaseModel):
    """Payload for comparing a resume directly against a job description."""

    resume_text: str = Field(min_length=20, description="Resume text content")
    job_text: str = Field(min_length=20, description="Job description text")
    job_title: str = Field(default="Target Position", max_length=150)
    candidate_name: str | None = None


class CandidateTextItem(BaseModel):
    """Candidate entry in ranking payload."""

    name: str = "Candidate"
    resume_text: str = Field(min_length=20)


class DirectRankingRequest(BaseModel):
    """Payload for ranking multiple candidates against a target job."""

    job_title: str = Field(default="Target Role")
    job_description: str = Field(min_length=20)
    resumes: list[CandidateTextItem] = Field(min_length=1)


@router.post(
    "/analyze",
    response_model=MatchAnalysisReport,
    summary="Analyze candidate-to-job match compatibility",
)
async def analyze_match(
    payload: DirectMatchRequest,
    resume_parser: ResumeParserService = Depends(get_resume_parser),
    job_parser: JobParserService = Depends(get_job_parser),
    matcher: MatchingEngineService = Depends(get_matching_service),
) -> MatchAnalysisReport:
    """
    Computes 5-dimension score, ATS compliance score, skill gap breakdown,
    and tailored recommendations between a resume and job description.
    """
    # 1. Parse resume
    doc = ExtractedDocument(
        raw_text=payload.resume_text,
        cleaned_text=payload.resume_text.strip(),
        total_pages=1,
        character_count=len(payload.resume_text),
        word_count=len(payload.resume_text.split()),
    )
    parsed_resume = resume_parser.parse(doc, filename="direct_submission.txt")
    if payload.candidate_name:
        parsed_resume.candidate_profile.contact.full_name = payload.candidate_name

    # 2. Parse job
    job_in = JobCreate(
        title=payload.job_title,
        description=payload.job_text,
    )
    parsed_job = job_parser.parse(job_in)

    # 3. Analyze match
    report = matcher.analyze_match(parsed_resume, parsed_job)
    return report


@router.post(
    "/rank",
    response_model=CandidateRankingResponse,
    summary="Rank a pool of candidate resumes against a job description",
)
async def rank_candidates(
    payload: DirectRankingRequest,
    resume_parser: ResumeParserService = Depends(get_resume_parser),
    job_parser: JobParserService = Depends(get_job_parser),
    matcher: MatchingEngineService = Depends(get_matching_service),
) -> CandidateRankingResponse:
    """
    Ranks multiple candidates against a single job description,
    returning a sorted leaderboard with score breakdowns and summaries.
    """
    job_in = JobCreate(
        title=payload.job_title,
        description=payload.job_description,
    )
    parsed_job = job_parser.parse(job_in)

    parsed_resumes = []
    for cand in payload.resumes:
        doc = ExtractedDocument(
            raw_text=cand.resume_text,
            cleaned_text=cand.resume_text.strip(),
            total_pages=1,
            character_count=len(cand.resume_text),
            word_count=len(cand.resume_text.split()),
        )
        p_res = resume_parser.parse(doc, filename=f"{cand.name}.txt")
        p_res.candidate_profile.contact.full_name = cand.name
        parsed_resumes.append(p_res)

    ranking_resp = matcher.rank_candidates(parsed_resumes, parsed_job)
    return ranking_resp
