"""
FastAPI Route Dependencies and Service Injection.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository
from app.services.ats_service import ATSService, ats_service
from app.services.embedding_service import EmbeddingService, embedding_service
from app.services.job_parser import JobParserService, job_parser_service
from app.services.matching_service import MatchingEngineService, matching_service
from app.services.pdf_service import BasePDFExtractor, pdf_extractor
from app.services.resume_parser import ResumeParserService, resume_parser_service
from app.services.skill_extractor import SkillExtractorService, skill_extractor_service


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding active async DB session."""
    async for session in get_db():
        yield session


def get_candidate_repo(session: AsyncSession = Depends(get_db_session)) -> CandidateRepository:
    """Dependency for CandidateRepository."""
    return CandidateRepository(session)


def get_job_repo(session: AsyncSession = Depends(get_db_session)) -> JobRepository:
    """Dependency for JobRepository."""
    return JobRepository(session)


def get_match_repo(session: AsyncSession = Depends(get_db_session)) -> MatchRepository:
    """Dependency for MatchRepository."""
    return MatchRepository(session)


def get_pdf_extractor() -> BasePDFExtractor:
    """Dependency for PDF extractor service."""
    return pdf_extractor


def get_resume_parser() -> ResumeParserService:
    """Dependency for Resume Parser service."""
    return resume_parser_service


def get_skill_extractor() -> SkillExtractorService:
    """Dependency for Skill Extractor service."""
    return skill_extractor_service


def get_job_parser() -> JobParserService:
    """Dependency for Job Parser service."""
    return job_parser_service


def get_embedding_service() -> EmbeddingService:
    """Dependency for Embedding service."""
    return embedding_service


def get_matching_service() -> MatchingEngineService:
    """Dependency for Matching Engine service."""
    return matching_service


def get_ats_service() -> ATSService:
    """Dependency for ATS service."""
    return ats_service
