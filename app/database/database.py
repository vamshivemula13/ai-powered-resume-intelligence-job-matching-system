"""
Database Connection and Session Lifecycle Management.

Configures SQLAlchemy 2.0 AsyncEngine and async session factory
compatible with PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.models  # noqa: F401 - Register all ORM models with Base metadata
from app.core.config import settings
from app.core.logging import get_logger
from app.models.base import Base

logger = get_logger(__name__)

# Initialize async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    future=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Initializes database tables defined in the Base metadata.
    Called during application lifespan startup.
    """
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an active async database session
    and guarantees safe commit or rollback on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
