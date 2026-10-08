"""
Application Configuration Module.

Uses Pydantic BaseSettings to read environment variables from `.env`
with strict type validation, default fallback values, and constraint checks.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings.
    Attributes are loaded from environment variables (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment & Metadata
    environment: str = Field(default="development", description="Runtime environment")
    project_name: str = Field(
        default="AI-Powered Resume Intelligence & Job Matching System",
        description="Public project name",
    )
    api_v1_str: str = Field(default="/api/v1", description="API v1 prefix")
    debug: bool = Field(default=True, description="Enable debug diagnostics")
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, description="Server port")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./resume_intelligence.db",
        description="SQLAlchemy Database connection URI",
    )
    database_echo: bool = Field(
        default=False, description="Log generated SQL queries to stdout"
    )

    # File Storage & Limits
    max_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum allowed PDF upload size in bytes",
    )
    allowed_mime_types: list[str] = Field(
        default=["application/pdf"],
        description="Permitted file MIME types",
    )
    storage_dir: Path = Field(
        default=Path("./data/resumes/uploads"),
        description="Directory for local resume PDF caching",
    )

    # NLP & Machine Learning Models
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="HuggingFace SentenceTransformers model tag",
    )
    spacy_model: str = Field(
        default="en_core_web_sm",
        description="spaCy linguistic pipeline package name",
    )

    # Multi-Factor Match Weights (Sum must normalize to 1.0)
    weight_skill_match: float = Field(
        default=0.35, ge=0.0, le=1.0, description="Weight for skill match"
    )
    weight_semantic_match: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for vector similarity"
    )
    weight_experience_match: float = Field(
        default=0.20, ge=0.0, le=1.0, description="Weight for tenure match"
    )
    weight_education_match: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Weight for degree match"
    )
    weight_project_match: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Weight for project relevance"
    )

    @field_validator("database_url")
    @classmethod
    def normalize_sqlite_async_url(cls, v: str) -> str:
        """
        Ensure SQLite URL uses the async aiosqlite driver for async SQLAlchemy.
        Converts 'sqlite:///path' to 'sqlite+aiosqlite:///path' if needed.
        """
        if v.startswith("sqlite://") and not v.startswith("sqlite+aiosqlite://"):
            return v.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return v

    @property
    def total_weight(self) -> float:
        """Calculate total sum of configured heuristic weights."""
        return round(
            self.weight_skill_match
            + self.weight_semantic_match
            + self.weight_experience_match
            + self.weight_education_match
            + self.weight_project_match,
            4,
        )

    def is_weights_valid(self) -> bool:
        """Check if total weights sum up to approximately 1.0 (with float tolerance)."""
        return abs(self.total_weight - 1.0) < 0.001


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Singleton accessor for cached Application Settings.
    The `@lru_cache` ensures `.env` is parsed only once across all imports.
    """
    return Settings()


# Global instance for convenient direct import
settings: Settings = get_settings()
