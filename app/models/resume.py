"""
Resume ORM Model.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.match import MatchResult


class Resume(Base, TimestampMixin):
    """Stores metadata, section text, and binary references for uploaded resumes."""

    __tablename__ = "resumes"

    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, default=1)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    sections_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="resumes")
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="resume", cascade="all, delete-orphan"
    )
