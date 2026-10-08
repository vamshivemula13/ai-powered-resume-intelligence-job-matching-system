"""
Skill Extraction and Taxonomy Matching Engine.

Loads configured skills and aliases from JSON taxonomy,
applies boundary-aware regex matching, and aggregates candidate competencies.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.exceptions import TaxonomyError
from app.core.logging import get_logger
from app.schemas.resume import ParsedResume, ResumeSectionType
from app.schemas.skill import ExtractedSkill, SkillCategory, SkillExtractionResult

logger = get_logger(__name__)


@dataclass
class CompiledSkillRule:
    """Compiled pattern rule representing a single canonical skill and its aliases."""

    canonical_name: str
    category: SkillCategory
    pattern: re.Pattern
    exact_boundary: bool
    case_sensitive: bool


class SkillExtractorService:
    """
    Extracts structured technical skills from unstructured text and parsed resumes.
    Uses configurable taxonomy without hard-coded rules in code.
    """

    DEFAULT_TAXONOMY_PATH = Path("./data/taxonomy/skills.json")

    def __init__(self, taxonomy_path: Path | str | None = None) -> None:
        self.taxonomy_path = Path(taxonomy_path or self.DEFAULT_TAXONOMY_PATH)
        self.rules: list[CompiledSkillRule] = []
        self._load_taxonomy()

    def _load_taxonomy(self) -> None:
        """Loads and compiles skill rules from the JSON taxonomy file."""
        if not self.taxonomy_path.exists():
            raise TaxonomyError(
                message=f"Taxonomy file not found at: {self.taxonomy_path}",
                details={"path": str(self.taxonomy_path)},
            )

        try:
            with open(self.taxonomy_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as exc:
            raise TaxonomyError(
                message=f"Invalid JSON syntax in taxonomy file: {exc}",
                details={"path": str(self.taxonomy_path)},
            ) from exc

        categories = data.get("categories", {})
        if not categories:
            raise TaxonomyError(
                message="Taxonomy file does not define any skill categories.",
                details={"path": str(self.taxonomy_path)},
            )

        compiled_rules: list[CompiledSkillRule] = []

        for category_name, skills_list in categories.items():
            category_enum = self._map_category_to_enum(category_name)

            for entry in skills_list:
                canonical = entry.get("canonical")
                if not canonical:
                    continue

                aliases = entry.get("aliases", [])
                exact_boundary = entry.get("exact_boundary", False)
                case_sensitive = entry.get("case_sensitive", False)

                regex = self._compile_skill_regex(canonical, aliases, exact_boundary, case_sensitive)

                compiled_rules.append(
                    CompiledSkillRule(
                        canonical_name=canonical,
                        category=category_enum,
                        pattern=regex,
                        exact_boundary=exact_boundary,
                        case_sensitive=case_sensitive,
                    )
                )

        self.rules = compiled_rules
        logger.info(
            "Skill taxonomy loaded successfully: %d rules across %d categories.",
            len(self.rules),
            len(categories),
        )

    def _compile_skill_regex(
        self, canonical: str, aliases: list[str], exact_boundary: bool, case_sensitive: bool
    ) -> re.Pattern:
        """
        Builds a robust regular expression pattern for a skill and its aliases.
        Special characters like '+', '.', and '/' are escaped appropriately.
        """
        all_terms = [canonical] + aliases
        escaped_terms: list[str] = []

        for term in all_terms:
            t = term.strip()
            if not t:
                continue

            # Special case for C++: allow 'c++', 'c ++'
            if t.lower() == "c++":
                escaped_terms.append(r"\bc\s*\+\+")
            # Special case for CI/CD: allow 'ci/cd', 'ci cd'
            elif t.lower() in ("ci/cd", "ci cd"):
                escaped_terms.append(r"\bci\s*[/]\s*cd\b")
            else:
                escaped_terms.append(r"\b" + re.escape(t) + r"\b")

        joined_pattern = "|".join(escaped_terms)
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.compile(f"(?:{joined_pattern})", flags)

    @staticmethod
    def _map_category_to_enum(category_name: str) -> SkillCategory:
        """Safely maps raw category strings to SkillCategory enum."""
        mapping = {
            "Programming Languages": SkillCategory.PROGRAMMING_LANGUAGES,
            "Backend": SkillCategory.BACKEND,
            "Database": SkillCategory.DATABASE,
            "Cloud": SkillCategory.CLOUD,
            "DevOps": SkillCategory.DEVOPS,
            "AI/ML": SkillCategory.AI_ML,
        }
        return mapping.get(category_name, SkillCategory.OTHER)

    def extract_from_text(self, text: str, is_skills_section: bool = False) -> list[ExtractedSkill]:
        """
        Scans a text block against compiled taxonomy rules and returns detected skills.
        """
        if not text:
            return []

        detected: list[ExtractedSkill] = []

        for rule in self.rules:
            matches = list(rule.pattern.finditer(text))
            if matches:
                occurrences = len(matches)
                first_match_text = matches[0].group(0)
                confidence = 1.0 if is_skills_section else 0.9

                detected.append(
                    ExtractedSkill(
                        canonical_name=rule.canonical_name,
                        category=rule.category,
                        confidence=confidence,
                        matched_text=first_match_text,
                        occurrences=occurrences,
                        is_in_skills_section=is_skills_section,
                    )
                )

        return detected

    def extract_from_resume(self, resume: ParsedResume) -> SkillExtractionResult:
        """
        Extracts skills across all resume sections with contextual confidence weighting.
        """
        # Map canonical_name -> ExtractedSkill for deduplication
        skill_map: dict[str, ExtractedSkill] = {}

        # 1. First scan explicit skills section (high priority)
        skills_text = resume.sections.get(ResumeSectionType.SKILLS, "")
        if skills_text:
            for skill in self.extract_from_text(skills_text, is_skills_section=True):
                skill_map[skill.canonical_name] = skill

        # 2. Next scan experience and projects sections
        exp_text = resume.sections.get(ResumeSectionType.EXPERIENCE, "")
        proj_text = resume.sections.get(ResumeSectionType.PROJECTS, "")
        body_text = f"{exp_text}\n{proj_text}".strip()

        if body_text:
            for skill in self.extract_from_text(body_text, is_skills_section=False):
                if skill.canonical_name in skill_map:
                    # Update occurrences
                    existing = skill_map[skill.canonical_name]
                    existing.occurrences += skill.occurrences
                else:
                    skill_map[skill.canonical_name] = skill

        # 3. Finally scan full text for any missing mentions
        for skill in self.extract_from_text(resume.cleaned_text, is_skills_section=False):
            if skill.canonical_name not in skill_map:
                skill_map[skill.canonical_name] = skill

        extracted_list = list(skill_map.values())

        # Build category breakdown
        categories_breakdown: dict[str, list[str]] = {}
        for s in extracted_list:
            cat_name = s.category.value
            if cat_name not in categories_breakdown:
                categories_breakdown[cat_name] = []
            categories_breakdown[cat_name].append(s.canonical_name)

        logger.info(
            "Extracted %d unique skills from resume '%s'.",
            len(extracted_list),
            resume.filename,
        )

        return SkillExtractionResult(
            skills=extracted_list,
            categories_breakdown=categories_breakdown,
            total_unique_skills=len(extracted_list),
        )


# Default singleton instance
skill_extractor_service = SkillExtractorService()
