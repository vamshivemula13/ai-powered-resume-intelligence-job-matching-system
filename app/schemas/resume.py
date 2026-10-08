"""
Resume Schemas Module.

Defines Pydantic representations for segmented resume sections,
parsing metadata, and full parsed document models.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.candidate import CandidateProfile


class ResumeSectionType(str, Enum):
    """Recognized resume semantic section types."""

    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    ACHIEVEMENTS = "achievements"
    UNKNOWN = "unknown"


class ParsedSection(BaseModel):
    """Individual segmented section of a resume."""

    model_config = ConfigDict(extra="ignore")

    section_type: ResumeSectionType
    header_title: str
    content: str
    character_count: int = Field(ge=0)


class ParsedResume(BaseModel):
    """Complete structured representation of a processed resume document."""

    model_config = ConfigDict(extra="ignore")

    filename: str = Field(default="resume.pdf", description="Source document filename")
    total_pages: int = Field(default=1, ge=1)
    is_scanned: bool = Field(default=False)
    candidate_profile: CandidateProfile = Field(default_factory=CandidateProfile)
    sections: dict[ResumeSectionType, str] = Field(
        default_factory=dict,
        description="Dictionary mapping section categories to their text content",
    )
    raw_text: str = Field(default="", description="Unsanitized raw extracted text")
    cleaned_text: str = Field(default="", description="Sanitized full text")

    def get_section_text(self, section_type: ResumeSectionType) -> str:
        """Helper to safely retrieve section text or empty string if missing."""
        return self.sections.get(section_type, "")
