"""
Match Scoring, ATS Report, and Ranking Schemas.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SkillMatchStatus(str, Enum):
    """Classification of candidate skill alignment."""

    STRONG_MATCH = "Strong Match"
    PARTIAL_MATCH = "Partial Match"
    MISSING = "Missing"


class SkillGapPriority(str, Enum):
    """Urgency / criticality of a missing skill."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class SkillGapItem(BaseModel):
    """Individual skill evaluation against job requirements."""

    model_config = ConfigDict(extra="ignore")

    skill_name: str
    status: SkillMatchStatus
    priority: SkillGapPriority
    category: str = "General"
    notes: str = ""


class ATSCheckItem(BaseModel):
    """Individual ATS audit parameter evaluation."""

    model_config = ConfigDict(extra="ignore")

    criterion: str
    passed: bool
    message: str


class ATSReport(BaseModel):
    """Complete ATS compliance audit."""

    model_config = ConfigDict(extra="ignore")

    ats_score: float = Field(ge=0.0, le=100.0)
    passed_checks: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    checklist: list[ATSCheckItem] = Field(default_factory=list)


class MatchBreakdown(BaseModel):
    """Multi-dimensional score breakdown across configured evaluation weights."""

    model_config = ConfigDict(extra="ignore")

    skill_score: float = Field(ge=0.0, le=100.0)
    semantic_score: float = Field(ge=0.0, le=100.0)
    experience_score: float = Field(ge=0.0, le=100.0)
    education_score: float = Field(ge=0.0, le=100.0)
    project_score: float = Field(ge=0.0, le=100.0)
    weights_used: dict[str, float] = Field(default_factory=dict)


class MatchAnalysisReport(BaseModel):
    """Comprehensive, explainable candidate-to-job matching report."""

    model_config = ConfigDict(extra="ignore")

    candidate_id: str | None = None
    candidate_name: str
    job_title: str
    overall_score: float = Field(ge=0.0, le=100.0)
    breakdown: MatchBreakdown
    ats_analysis: ATSReport
    skill_gap: list[SkillGapItem] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_critical_skills: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CandidateRankingItem(BaseModel):
    """Single candidate position in ranked comparison list."""

    model_config = ConfigDict(extra="ignore")

    rank: int = Field(ge=1)
    candidate_name: str
    candidate_id: str | None = None
    overall_score: float = Field(ge=0.0, le=100.0)
    skill_score: float = Field(ge=0.0, le=100.0)
    semantic_score: float = Field(ge=0.0, le=100.0)
    summary: str


class CandidateRankingResponse(BaseModel):
    """Ranked leaderboard comparing multiple resumes against a job description."""

    model_config = ConfigDict(extra="ignore")

    job_title: str
    total_candidates: int
    rankings: list[CandidateRankingItem] = Field(default_factory=list)
