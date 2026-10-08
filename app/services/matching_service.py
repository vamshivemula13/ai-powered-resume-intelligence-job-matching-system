"""
Multi-Factor Matching and Scoring Engine.

Calculates multi-dimensional compatibility scores, executes skill gap analysis,
generates explainable feedback recommendations, and ranks candidate pools.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.job import JobParsed
from app.schemas.match import (
    CandidateRankingItem,
    CandidateRankingResponse,
    MatchAnalysisReport,
    MatchBreakdown,
    SkillGapItem,
    SkillGapPriority,
    SkillMatchStatus,
)
from app.schemas.resume import ParsedResume, ResumeSectionType
from app.services.ats_service import ats_service
from app.services.embedding_service import embedding_service
from app.services.skill_extractor import skill_extractor_service

logger = get_logger(__name__)


class MatchingEngineService:
    """
    Core algorithmic engine computing composite scores across 5 dimensions:
    1. Skill Match        (35%)
    2. Semantic Vector    (25%)
    3. Experience Tenure  (20%)
    4. Education Degree   (10%)
    5. Project Relevance  (10%)
    """

    DEGREE_RANKS = {
        "associate": 1,
        "bachelor's": 2,
        "bachelor": 2,
        "master's": 3,
        "master": 3,
        "ph.d.": 4,
        "phd": 4,
        "doctorate": 4,
    }

    def analyze_match(self, resume: ParsedResume, job: JobParsed) -> MatchAnalysisReport:
        """
        Executes complete multi-dimensional match evaluation between a parsed resume and job description.
        """
        # Extract candidate skills
        cand_skill_res = skill_extractor_service.extract_from_resume(resume)
        cand_skills = cand_skill_res.get_skill_names()

        req_skills = set(job.requirements.required_skills)
        pref_skills = set(job.requirements.preferred_skills)

        # 1. Dimension Scores
        skill_score = self._compute_skill_score(cand_skills, req_skills, pref_skills)
        semantic_score = self._compute_semantic_score(resume.cleaned_text, job.cleaned_description)
        exp_score = self._compute_experience_score(
            resume.candidate_profile.estimated_experience_years,
            job.requirements.min_experience_years,
        )
        edu_score = self._compute_education_score(
            [e.degree for e in resume.candidate_profile.education_entries],
            job.requirements.min_education_level,
        )
        proj_score = self._compute_project_score(
            resume.get_section_text(ResumeSectionType.PROJECTS),
            job.cleaned_description,
            fallback_score=semantic_score,
        )

        # 2. Weighted Overall Composite Score
        overall_score = round(
            (skill_score * settings.weight_skill_match)
            + (semantic_score * settings.weight_semantic_match)
            + (exp_score * settings.weight_experience_match)
            + (edu_score * settings.weight_education_match)
            + (proj_score * settings.weight_project_match),
            1,
        )
        overall_score = max(0.0, min(100.0, overall_score))

        # 3. Skill Gap Analysis
        skill_gaps = self._analyze_skill_gaps(cand_skill_res, req_skills, pref_skills)

        # 4. ATS Compliance Audit
        ats_report = ats_service.analyze(resume)

        # 5. Explainable Strengths & Missing Critical Skills
        strengths, missing_critical, recommendations = self._generate_insights(
            resume=resume,
            job=job,
            cand_skills=cand_skills,
            skill_score=skill_score,
            exp_score=exp_score,
            overall_score=overall_score,
            skill_gaps=skill_gaps,
        )

        breakdown = MatchBreakdown(
            skill_score=skill_score,
            semantic_score=semantic_score,
            experience_score=exp_score,
            education_score=edu_score,
            project_score=proj_score,
            weights_used={
                "skill_match": settings.weight_skill_match,
                "semantic_match": settings.weight_semantic_match,
                "experience_match": settings.weight_experience_match,
                "education_match": settings.weight_education_match,
                "project_match": settings.weight_project_match,
            },
        )

        cand_name = resume.candidate_profile.contact.full_name or "Candidate"

        logger.info(
            "Match analysis complete for '%s' vs '%s': Score=%.1f%% (Skills=%.1f%%, Semantics=%.1f%%)",
            cand_name,
            job.title,
            overall_score,
            skill_score,
            semantic_score,
        )

        return MatchAnalysisReport(
            candidate_name=cand_name,
            job_title=job.title,
            overall_score=overall_score,
            breakdown=breakdown,
            ats_analysis=ats_report,
            skill_gap=skill_gaps,
            strengths=strengths,
            missing_critical_skills=missing_critical,
            recommendations=recommendations,
        )

    def rank_candidates(
        self, resumes: list[ParsedResume], job: JobParsed
    ) -> CandidateRankingResponse:
        """
        Ranks a pool of candidates against a single job description in descending order of overall score.
        """
        evaluations: list[tuple[ParsedResume, MatchAnalysisReport]] = []

        for resume in resumes:
            report = self.analyze_match(resume, job)
            evaluations.append((resume, report))

        # Sort descending by overall_score, tie-break by skill_score
        evaluations.sort(
            key=lambda item: (item[1].overall_score, item[1].breakdown.skill_score),
            reverse=True,
        )

        ranking_items: list[CandidateRankingItem] = []
        for rank_idx, (resume, rep) in enumerate(evaluations, start=1):
            name = resume.candidate_profile.contact.full_name or f"Candidate {rank_idx}"
            summary = (
                f"{'Top candidate' if rep.overall_score >= 80 else 'Qualified' if rep.overall_score >= 60 else 'Needs development'}: "
                f"{len(rep.strengths)} strengths identified, "
                f"{len(rep.missing_critical_skills)} critical skill gaps."
            )
            ranking_items.append(
                CandidateRankingItem(
                    rank=rank_idx,
                    candidate_name=name,
                    overall_score=rep.overall_score,
                    skill_score=rep.breakdown.skill_score,
                    semantic_score=rep.breakdown.semantic_score,
                    summary=summary,
                )
            )

        return CandidateRankingResponse(
            job_title=job.title,
            total_candidates=len(resumes),
            rankings=ranking_items,
        )

    def _compute_skill_score(
        self, cand_skills: set[str], req_skills: set[str], pref_skills: set[str]
    ) -> float:
        """Calculates 0-100 score prioritizing required skills (80%) over preferred skills (20%)."""
        if not req_skills and not pref_skills:
            return 100.0

        score = 0.0
        # Required skills component
        if req_skills:
            req_matched = len(cand_skills & req_skills)
            req_pct = req_matched / len(req_skills)
            score += req_pct * 80.0
        else:
            score += 80.0

        # Preferred skills component
        if pref_skills:
            pref_matched = len(cand_skills & pref_skills)
            pref_pct = pref_matched / len(pref_skills)
            score += pref_pct * 20.0
        else:
            score += 20.0

        return round(min(score, 100.0), 1)

    @staticmethod
    def _compute_semantic_score(resume_text: str, job_text: str) -> float:
        """Computes dense vector similarity score."""
        sim = embedding_service.calculate_similarity(resume_text, job_text)
        return round(sim * 100.0, 1)

    @staticmethod
    def _compute_experience_score(cand_years: float, req_years: float) -> float:
        """Evaluates experience tenure against job requirement."""
        if req_years <= 0.0 or cand_years >= req_years:
            return 100.0
        ratio = cand_years / req_years
        return round(ratio * 100.0, 1)

    def _compute_education_score(
        self, cand_degrees: list[str], min_edu: str | None
    ) -> float:
        """Compares highest candidate degree against minimum job hurdle."""
        if not min_edu:
            return 100.0

        min_rank = self.DEGREE_RANKS.get(min_edu.strip().lower(), 2)
        if not cand_degrees:
            return 60.0  # Experience may substitute

        max_cand_rank = max(
            [self.DEGREE_RANKS.get(d.strip().lower(), 1) for d in cand_degrees] or [1]
        )

        if max_cand_rank >= min_rank:
            return 100.0
        return 75.0

    @staticmethod
    def _compute_project_score(
        project_text: str, job_text: str, fallback_score: float
    ) -> float:
        """Measures alignment of candidate projects with job requirements."""
        if not project_text.strip():
            # If candidate omitted explicit projects section, scale down semantic score slightly
            return round(fallback_score * 0.9, 1)
        sim = embedding_service.calculate_similarity(project_text, job_text)
        return round(sim * 100.0, 1)

    def _analyze_skill_gaps(
        self, cand_skill_res, req_skills: set[str], pref_skills: set[str]
    ) -> list[SkillGapItem]:
        """Classifies each job competency into Strong Match, Partial Match, or Missing."""
        cand_skills = cand_skill_res.get_skill_names()
        cand_categories = cand_skill_res.categories_breakdown
        gaps: list[SkillGapItem] = []

        # Analyze Required Skills
        for skill in sorted(req_skills):
            if skill in cand_skills:
                gaps.append(
                    SkillGapItem(
                        skill_name=skill,
                        status=SkillMatchStatus.STRONG_MATCH,
                        priority=SkillGapPriority.CRITICAL,
                        category="Required Skill",
                        notes="Candidate explicitly demonstrates competency.",
                    )
                )
            else:
                # Check for category overlap (Partial Match)
                partial = self._find_category_overlap(skill, cand_categories)
                if partial:
                    gaps.append(
                        SkillGapItem(
                            skill_name=skill,
                            status=SkillMatchStatus.PARTIAL_MATCH,
                            priority=SkillGapPriority.HIGH,
                            category="Required Skill",
                            notes=f"Candidate possesses related alternative: {partial}.",
                        )
                    )
                else:
                    gaps.append(
                        SkillGapItem(
                            skill_name=skill,
                            status=SkillMatchStatus.MISSING,
                            priority=SkillGapPriority.CRITICAL,
                            category="Required Skill",
                            notes="Required core competency not detected on resume.",
                        )
                    )

        # Analyze Preferred Skills
        for skill in sorted(pref_skills):
            if skill in cand_skills:
                gaps.append(
                    SkillGapItem(
                        skill_name=skill,
                        status=SkillMatchStatus.STRONG_MATCH,
                        priority=SkillGapPriority.MEDIUM,
                        category="Preferred Skill",
                        notes="Candidate satisfies preferred qualification.",
                    )
                )
            else:
                gaps.append(
                    SkillGapItem(
                        skill_name=skill,
                        status=SkillMatchStatus.MISSING,
                        priority=SkillGapPriority.LOW,
                        category="Preferred Skill",
                        notes="Preferred bonus skill absent (non-disqualifying).",
                    )
                )

        return gaps

    @staticmethod
    def _find_category_overlap(missing_skill: str, cand_categories: dict[str, list[str]]) -> str | None:
        """Identifies if candidate has alternative competencies in the same category."""
        # Find which category missing_skill belongs to
        cloud_skills = {"AWS", "Azure", "GCP"}
        db_skills = {"PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite"}

        if missing_skill in cloud_skills:
            cand_cloud = [s for s in cand_skills_in_cat(cand_categories, "Cloud") if s != missing_skill]
            if cand_cloud:
                return ", ".join(cand_cloud)

        if missing_skill in db_skills:
            cand_dbs = [s for s in cand_skills_in_cat(cand_categories, "Database") if s != missing_skill]
            if cand_dbs:
                return ", ".join(cand_dbs)

        return None

    @staticmethod
    def _generate_insights(
        resume: ParsedResume,
        job: JobParsed,
        cand_skills: set[str],
        skill_score: float,
        exp_score: float,
        overall_score: float,
        skill_gaps: list[SkillGapItem],
    ) -> tuple[list[str], list[str], list[str]]:
        """Generates actionable strengths, missing critical skills, and resume recommendations."""
        strengths: list[str] = []
        missing_critical: list[str] = []
        recommendations: list[str] = []

        # Strengths
        for gap in skill_gaps:
            if gap.status == SkillMatchStatus.STRONG_MATCH and gap.priority == SkillGapPriority.CRITICAL:
                strengths.append(f"Strong hands-on {gap.skill_name} experience matching core requirements")

        if exp_score >= 100.0 and job.requirements.min_experience_years > 0:
            strengths.append(
                f"Meets or exceeds experience requirement ({resume.candidate_profile.estimated_experience_years:.1f} yrs vs {job.requirements.min_experience_years:.1f} yrs required)"
            )

        # Missing Critical
        for gap in skill_gaps:
            if gap.status == SkillMatchStatus.MISSING and gap.priority == SkillGapPriority.CRITICAL:
                missing_critical.append(gap.skill_name)

        # Actionable Suggestions
        if missing_critical:
            recommendations.append(
                f"Highlight projects or practical coursework utilizing: {', '.join(missing_critical[:4])}"
            )

        if ResumeSectionType.PROJECTS not in resume.sections:
            recommendations.append(
                "Add a dedicated 'Key Projects' section highlighting measurable engineering achievements"
            )

        if resume.candidate_profile.estimated_experience_years < job.requirements.min_experience_years:
            deficit = job.requirements.min_experience_years - resume.candidate_profile.estimated_experience_years
            recommendations.append(
                f"Address the {deficit:.1f}-year experience gap by emphasizing high-impact accomplishments"
            )

        if not recommendations:
            recommendations.append("Resume strongly aligns with job requirements. Prepare for in-depth technical interview.")

        return strengths[:5], missing_critical, recommendations[:5]


def cand_skills_in_cat(categories: dict[str, list[str]], cat_name: str) -> list[str]:
    """Helper to return candidate skills in a given category."""
    return categories.get(cat_name, [])


# Singleton matching engine service
matching_service = MatchingEngineService()
