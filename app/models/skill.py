"""
Skill and Association ORM Models.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import Job


class Skill(Base, TimestampMixin):
    """Normalized master table of technical competencies."""

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Relationships
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    job_skills: Mapped[list["JobSkill"]] = relationship(
        "JobSkill", back_populates="skill", cascade="all, delete-orphan"
    )


class CandidateSkill(Base, TimestampMixin):
    """Association table linking candidates to their detected skills."""

    __tablename__ = "candidate_skills"

    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skills.id", ondelete="CASCADE"), index=True
    )
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_in_skills_section: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="candidate_skills")


class JobSkill(Base, TimestampMixin):
    """Association table linking job descriptions to required and preferred skills."""

    __tablename__ = "job_skills"

    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skills.id", ondelete="CASCADE"), index=True
    )
    priority: Mapped[str] = mapped_column(String(20), default="required")  # required / preferred

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="job_skills")
