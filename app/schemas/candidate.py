"""
Candidate Domain Schemas.

Pydantic models representing parsed candidate contact details,
educational history, and high-level candidate profiles.
"""

from pydantic import BaseModel, ConfigDict, Field


class ContactInfo(BaseModel):
    """Extracted contact and social footprint information."""

    model_config = ConfigDict(extra="ignore")

    full_name: str | None = Field(default=None, description="Candidate full name")
    email: str | None = Field(default=None, description="Primary email address")
    phone: str | None = Field(default=None, description="Primary phone number")
    linkedin_url: str | None = Field(default=None, description="LinkedIn profile URL")
    github_url: str | None = Field(default=None, description="GitHub profile URL")
    portfolio_url: str | None = Field(default=None, description="Personal portfolio URL")


class EducationEntry(BaseModel):
    """Individual degree or certification entry detected in resume text."""

    model_config = ConfigDict(extra="ignore")

    degree: str = Field(description="Degree title (e.g., B.S., M.S., Ph.D., High School)")
    field_of_study: str | None = Field(
        default=None, description="Major or specialization (e.g., Computer Science)"
    )
    institution: str | None = Field(
        default=None, description="University or college name"
    )
    year: int | None = Field(default=None, description="Graduation year if detected")


class CandidateProfile(BaseModel):
    """Consolidated profile extracted from parsed resume content."""

    model_config = ConfigDict(extra="ignore")

    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str | None = Field(default=None, description="Executive summary text")
    estimated_experience_years: float = Field(
        default=0.0, ge=0.0, description="Estimated total professional experience in years"
    )
    education_entries: list[EducationEntry] = Field(
        default_factory=list, description="Extracted education credentials"
    )
