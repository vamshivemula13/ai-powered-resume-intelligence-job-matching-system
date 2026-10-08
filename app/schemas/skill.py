"""
Skill Domain Schemas.

Pydantic models representing extracted skills, categories,
alias mappings, and taxonomy extraction results.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SkillCategory(str, Enum):
    """Categorization tags for technical competencies."""

    PROGRAMMING_LANGUAGES = "Programming Languages"
    BACKEND = "Backend"
    DATABASE = "Database"
    CLOUD = "Cloud"
    DEVOPS = "DevOps"
    AI_ML = "AI/ML"
    OTHER = "Other"


class ExtractedSkill(BaseModel):
    """Represents a single verified skill detected in candidate or job text."""

    model_config = ConfigDict(extra="ignore")

    canonical_name: str = Field(description="Standardized name (e.g. 'PostgreSQL', 'FastAPI')")
    category: SkillCategory = Field(default=SkillCategory.OTHER)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    matched_text: str = Field(description="Exact phrase matched in raw document")
    occurrences: int = Field(default=1, ge=1)
    is_in_skills_section: bool = Field(
        default=False, description="Flagged true if skill was explicitly in skills block"
    )


class SkillExtractionResult(BaseModel):
    """Aggregated output from skill extraction pipeline."""

    model_config = ConfigDict(extra="ignore")

    skills: list[ExtractedSkill] = Field(default_factory=list)
    categories_breakdown: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Dictionary mapping each category to its canonical skill list",
    )
    total_unique_skills: int = Field(default=0, ge=0)

    def has_skill(self, skill_name: str) -> bool:
        """Helper to quickly check if a canonical skill exists in the result."""
        target = skill_name.strip().lower()
        return any(s.canonical_name.lower() == target for s in self.skills)

    def get_skill_names(self) -> set[str]:
        """Returns set of all detected canonical skill names."""
        return {s.canonical_name for s in self.skills}
