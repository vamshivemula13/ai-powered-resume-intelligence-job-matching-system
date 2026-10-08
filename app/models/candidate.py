"""
Candidate ORM Model.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.match import MatchResult
    from app.models.resume import Resume
    from app.models.skill import CandidateSkill


class Candidate(Base, TimestampMixin):
    """Normalized Candidate table storing personal footprint and aggregate metrics."""

    __tablename__ = "candidates"

    full_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(120), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_experience_years: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume", back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="candidate", cascade="all, delete-orphan"
    )
