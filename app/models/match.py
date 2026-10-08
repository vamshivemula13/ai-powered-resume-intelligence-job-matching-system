"""
Match Result ORM Model.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import Job
    from app.models.resume import Resume


class MatchResult(Base, TimestampMixin):
    """Stores composite match analysis, factor scores, skill gaps, and recommendations."""

    __tablename__ = "match_results"

    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )

    # Composite & Dimension Scores (0.0 to 100.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, nullable=False)
    project_score: Mapped[float] = mapped_column(Float, nullable=False)
    ats_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Detailed Analysis Payloads
    skill_gap_json: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations_json: Mapped[list] = mapped_column(JSON, default=list)
    strengths_json: Mapped[list] = mapped_column(JSON, default=list)

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="match_results")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="match_results")
    job: Mapped["Job"] = relationship("Job", back_populates="match_results")
