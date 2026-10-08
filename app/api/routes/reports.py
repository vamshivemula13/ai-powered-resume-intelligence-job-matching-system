"""
Health, Candidate Lookup, and Skill Taxonomy API Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_candidate_repo,
    get_db_session,
    get_skill_extractor,
)
from app.core.config import settings
from app.repositories.candidate_repository import CandidateRepository
from app.services.skill_extractor import SkillExtractorService

router = APIRouter(tags=["Reports & System"])


@router.get(
    "/health",
    summary="System health and component diagnostics",
)
async def health_check(
    session: AsyncSession = Depends(get_db_session),
    skill_ext: SkillExtractorService = Depends(get_skill_extractor),
):
    """Verifies database connectivity, configuration status, and taxonomy health."""
    db_ok = True
    db_error = None
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    return {
        "status": "healthy" if db_ok else "degraded",
        "project": settings.project_name,
        "environment": settings.environment,
        "database": {"connected": db_ok, "driver": "async", "error": db_error},
        "taxonomy": {"rules_count": len(skill_ext.rules)},
        "weights": {
            "skill": settings.weight_skill_match,
            "semantic": settings.weight_semantic_match,
            "experience": settings.weight_experience_match,
            "education": settings.weight_education_match,
            "project": settings.weight_project_match,
        },
    }


@router.get(
    "/candidates/{candidate_id}",
    summary="Get candidate profile and match records",
)
async def get_candidate_profile(
    candidate_id: str,
    cand_repo: CandidateRepository = Depends(get_candidate_repo),
):
    """Fetches candidate profile, resumes, and historical evaluations."""
    candidate = await cand_repo.get_with_details(candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID '{candidate_id}' not found.",
        )

    return {
        "id": candidate.id,
        "full_name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "linkedin_url": candidate.linkedin_url,
        "github_url": candidate.github_url,
        "estimated_experience_years": candidate.estimated_experience_years,
        "resumes_count": len(candidate.resumes),
        "matches_count": len(candidate.match_results),
    }


@router.get(
    "/taxonomy",
    summary="Get supported skills taxonomy summary",
)
async def get_taxonomy_summary(
    skill_ext: SkillExtractorService = Depends(get_skill_extractor),
):
    """Returns active taxonomy categories and registered canonical technologies."""
    categories: dict[str, list[str]] = {}
    for rule in skill_ext.rules:
        cat_name = rule.category.value
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(rule.canonical_name)

    return {
        "total_skills": len(skill_ext.rules),
        "categories": categories,
    }
