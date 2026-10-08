"""
Unit Tests for Skill Extraction & Taxonomy Engine (app/services/skill_extractor.py).
"""

import pytest

from app.core.exceptions import TaxonomyError
from app.schemas.resume import ParsedResume, ResumeSectionType
from app.services.skill_extractor import (
    SkillExtractorService,
    skill_extractor_service,
)


def test_extract_skills_canonical_and_categories() -> None:
    """Verify detection of canonical skills across multiple categories."""
    text = (
        "Architected scalable microservices using Python, FastAPI, and PostgreSQL. "
        "Deployed on AWS using Docker and Kubernetes with automated CI/CD pipelines."
    )
    result = skill_extractor_service.extract_from_text(text, is_skills_section=True)
    detected_names = {s.canonical_name for s in result}

    expected = {"Python", "FastAPI", "PostgreSQL", "AWS", "Docker", "Kubernetes", "CI/CD", "Microservices"}
    assert expected.issubset(detected_names)


def test_alias_resolution_to_canonical() -> None:
    """Verify colloquial abbreviations and aliases resolve to canonical names."""
    text = "Proficient in postgres, k8s, drf, and py."
    result = skill_extractor_service.extract_from_text(text)
    detected_names = {s.canonical_name for s in result}

    assert "PostgreSQL" in detected_names  # from 'postgres'
    assert "Kubernetes" in detected_names  # from 'k8s'
    assert "Django" in detected_names      # from 'drf'
    assert "Python" in detected_names      # from 'py'


def test_avoid_false_positives_for_short_terms() -> None:
    """Verify word boundaries prevent false positives for short terms like 'Go' or 'C'."""
    text = "We are going to the cloud on Tuesday with good class results."
    result = skill_extractor_service.extract_from_text(text)
    detected_names = {s.canonical_name for s in result}

    assert "Go" not in detected_names
    assert "C" not in detected_names


def test_extract_from_parsed_resume_structure() -> None:
    """Verify extraction across parsed resume sections with category aggregation."""
    resume = ParsedResume(
        filename="test_dev.pdf",
        sections={
            ResumeSectionType.SKILLS: "Python, FastAPI, Redis, Docker, PyTorch",
            ResumeSectionType.EXPERIENCE: "Used FastAPI and Redis to build high-speed APIs.",
        },
        cleaned_text="Python, FastAPI, Redis, Docker, PyTorch\nUsed FastAPI and Redis to build high-speed APIs.",
    )

    result = skill_extractor_service.extract_from_resume(resume)

    assert result.has_skill("FastAPI") is True
    assert result.has_skill("Python") is True
    assert result.has_skill("Redis") is True
    assert result.has_skill("Docker") is True
    assert result.has_skill("PyTorch") is True

    # Check category grouping
    breakdown = result.categories_breakdown
    assert "Programming Languages" in breakdown
    assert "Backend" in breakdown
    assert "Database" in breakdown
    assert "DevOps" in breakdown
    assert "AI/ML" in breakdown

    # FastAPI was in both skills and experience, so occurrences should be at least 2
    fastapi_skill = next(s for s in result.skills if s.canonical_name == "FastAPI")
    assert fastapi_skill.occurrences >= 2
    assert fastapi_skill.is_in_skills_section is True


def test_missing_taxonomy_raises_taxonomy_error(tmp_path) -> None:
    """Verify that a nonexistent taxonomy path raises a domain TaxonomyError."""
    missing_file = tmp_path / "missing_taxonomy.json"
    with pytest.raises(TaxonomyError) as exc_info:
        SkillExtractorService(taxonomy_path=missing_file)

    assert exc_info.value.code == "TAXONOMY_ERROR"
    assert "not found" in exc_info.value.message.lower()
