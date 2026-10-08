"""
Unit Tests for Application Configuration (app/core/config.py).
"""

from app.core.config import Settings, get_settings


def test_settings_loaded_from_env() -> None:
    """Verify that settings correctly load attributes from environment."""
    settings = get_settings()
    assert settings.environment == "development"
    assert "AI-Powered Resume Intelligence" in settings.project_name
    assert settings.api_v1_str == "/api/v1"
    assert settings.debug is True
    assert settings.host == "0.0.0.0"
    # Port may be 8080 when injected by Cloud Run/container runtime or 8000 from default
    assert isinstance(settings.port, int) and settings.port > 0


def test_sqlite_url_normalization() -> None:
    """
    Verify that standard sqlite URLs are normalized to async aiosqlite URLs.
    This prevents SQLAlchemy runtime failures when executing async sessions.
    """
    custom_settings = Settings(
        database_url="sqlite:///./test.db",
        _env_file=None,
    )
    assert custom_settings.database_url == "sqlite+aiosqlite:///./test.db"


def test_weight_validation() -> None:
    """Verify that matching engine weights are correctly calculated and sum to 1.0."""
    settings = get_settings()
    assert settings.is_weights_valid() is True
    assert settings.total_weight == 1.0
    assert settings.weight_skill_match == 0.35
    assert settings.weight_semantic_match == 0.25
    assert settings.weight_experience_match == 0.20
    assert settings.weight_education_match == 0.10
    assert settings.weight_project_match == 0.10


def test_settings_singleton_caching() -> None:
    """Verify that get_settings() returns the same cached instance via @lru_cache."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
