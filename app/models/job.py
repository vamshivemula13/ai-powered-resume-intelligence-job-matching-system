"""
Job ORM Model.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.match import MatchResult
    from app.models.skill import JobSkill


class Job(Base, TimestampMixin):
    """Stores job description requirements, qualifications, and role metadata."""

    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    min_experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    min_education_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    responsibilities_json: Mapped[list] = mapped_column(JSON, default=list)

    # Relationships
    skills: Mapped[list["JobSkill"]] = relationship(
        "JobSkill", back_populates="job", cascade="all, delete-orphan"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="job", cascade="all, delete-orphan"
    )
