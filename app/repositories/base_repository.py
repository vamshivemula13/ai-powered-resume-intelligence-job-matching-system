"""
Generic Base Repository.
"""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing standard CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: str) -> ModelType | None:
        """Fetch record by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Fetch page of records."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, entity: ModelType) -> ModelType:
        """Add record and flush."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Delete record."""
        await self.session.delete(entity)
        await self.session.flush()
