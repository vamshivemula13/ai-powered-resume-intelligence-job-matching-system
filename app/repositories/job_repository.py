"""
Job Repository.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository handling Job postings and associations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Job, session)

    async def get_with_skills(self, job_id: str) -> Job | None:
        """Fetch job with eagerly loaded associated skills."""
        result = await self.session.execute(
            select(Job)
            .options(selectinload(Job.skills))
            .where(Job.id == job_id)
        )
        return result.scalars().first()
