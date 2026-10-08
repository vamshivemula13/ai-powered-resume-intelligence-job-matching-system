"""
Candidate Repository.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.repositories.base_repository import BaseRepository


class CandidateRepository(BaseRepository[Candidate]):
    """Repository handling Candidate persistence, resumes, and associations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Candidate, session)

    async def get_by_email(self, email: str) -> Candidate | None:
        """Find candidate by email address."""
        result = await self.session.execute(
            select(Candidate).where(Candidate.email == email)
        )
        return result.scalars().first()

    async def get_with_details(self, candidate_id: str) -> Candidate | None:
        """Fetch candidate with eagerly loaded resumes and skills."""
        result = await self.session.execute(
            select(Candidate)
            .options(
                selectinload(Candidate.resumes),
                selectinload(Candidate.skills),
                selectinload(Candidate.match_results),
            )
            .where(Candidate.id == candidate_id)
        )
        return result.scalars().first()
