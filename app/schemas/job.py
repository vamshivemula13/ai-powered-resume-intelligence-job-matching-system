"""
Job Domain Schemas.

Pydantic models representing job postings, required and preferred skills,
experience tenure requirements, and parsed job requirement structures.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JobRequirementPriority(str, Enum):
    """Priority level for job competencies."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    OPTIONAL = "optional"


class SkillRequirement(BaseModel):
    """Specification of an individual skill required or preferred by a job."""

    model_config = ConfigDict(extra="ignore")

    canonical_name: str
    priority: JobRequirementPriority = JobRequirementPriority.REQUIRED
    min_years_experience: float | None = None


class JobRequirements(BaseModel):
    """Structured decomposition of qualifications requested in a job description."""

    model_config = ConfigDict(extra="ignore")

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float = Field(default=0.0, ge=0.0)
    min_education_level: str | None = Field(
        default=None, description="Minimum expected degree (e.g. 'Bachelor's', 'Master's')"
    )
    responsibilities: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)

    @property
    def all_skills(self) -> set[str]:
        """Union of required and preferred canonical skills."""
        return set(self.required_skills) | set(self.preferred_skills)


class JobCreate(BaseModel):
    """Payload for submitting a new job description."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=2, max_length=150, description="Job role title")
    description: str = Field(min_length=20, description="Full job description text")
    company: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    is_remote: bool = Field(default=False)


class JobParsed(BaseModel):
    """Enriched, parsed representation of a job description."""

    model_config = ConfigDict(extra="ignore")

    title: str
    company: str | None = None
    location: str | None = None
    is_remote: bool = False
    raw_description: str
    cleaned_description: str
    requirements: JobRequirements
    total_skills_detected: int = Field(default=0, ge=0)
