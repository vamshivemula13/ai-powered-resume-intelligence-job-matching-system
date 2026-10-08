"""
Match Result Repository.
"""

from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import MatchResult
from app.repositories.base_repository import BaseRepository


class MatchRepository(BaseRepository[MatchResult]):
    """Repository managing match scoring results, reports, and rankings."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MatchResult, session)

    async def get_by_job_ranked(self, job_id: str, limit: int = 50) -> Sequence[MatchResult]:
        """Fetch candidates for a job sorted descending by overall match score."""
        result = await self.session.execute(
            select(MatchResult)
            .options(
                selectinload(MatchResult.candidate),
                selectinload(MatchResult.resume),
            )
            .where(MatchResult.job_id == job_id)
            .order_by(desc(MatchResult.overall_score))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_with_relations(self, match_id: str) -> MatchResult | None:
        """Fetch match result with candidate, resume, and job relations."""
        result = await self.session.execute(
            select(MatchResult)
            .options(
                selectinload(MatchResult.candidate),
                selectinload(MatchResult.resume),
                selectinload(MatchResult.job),
            )
            .where(MatchResult.id == match_id)
        )
        return result.scalars().first()
