"""
Job Description Parser Service.

Decomposes raw job postings into structured requirements:
required skills, preferred skills, minimum experience tenure,
minimum education credential, and key responsibilities.
"""

import re
from enum import Enum

from app.core.logging import get_logger
from app.schemas.job import JobCreate, JobParsed, JobRequirements
from app.services.pdf_service import TextSanitizer
from app.services.skill_extractor import skill_extractor_service

logger = get_logger(__name__)


class JobSectionType(str, Enum):
    """Semantic sections common in job descriptions."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    RESPONSIBILITIES = "responsibilities"
    ABOUT_ROLE = "about_role"
    UNKNOWN = "unknown"


class JobParserService:
    """
    Parses unstructured job description text into a structured JobRequirements model.
    """

    SECTION_HEADER_MAP: dict[JobSectionType, list[str]] = {
        JobSectionType.REQUIRED: [
            "required qualifications",
            "minimum qualifications",
            "requirements",
            "what you need",
            "must have",
            "basic qualifications",
            "key requirements",
            "required skills",
            "qualifications",
        ],
        JobSectionType.PREFERRED: [
            "preferred qualifications",
            "nice to have",
            "bonus points",
            "bonus qualifications",
            "desired qualifications",
            "pluses",
            "good to have",
            "preferred skills",
            "what will set you apart",
        ],
        JobSectionType.RESPONSIBILITIES: [
            "responsibilities",
            "what you'll do",
            "what you will do",
            "duties",
            "role overview",
            "day to day",
            "key responsibilities",
            "the role",
        ],
    }

    # Regex for experience requirements (e.g., '3+ years of experience', 'minimum 5 years')
    EXP_REQ_PATTERNS = [
        re.compile(
            r"(?:minimum|at least)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years|yrs)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\b(?:\s*of)?\s*(?:relevant|hands-on|professional)?\s*(?:experience|exp)",
            re.IGNORECASE,
        ),
    ]

    # Education degree hierarchy
    EDUCATION_HIERARCHY = [
        (re.compile(r"\b(Ph\.?D\.?|Doctorate)\b", re.IGNORECASE), "Ph.D."),
        (re.compile(r"\b(Master'?s|M\.?S\.?|M\.?Tech)\b", re.IGNORECASE), "Master's"),
        (re.compile(r"\b(Bachelor'?s|B\.?S\.?|B\.?Tech|B\.?E\.?)\b", re.IGNORECASE), "Bachelor's"),
        (re.compile(r"\b(Associate'?s|Associate Degree)\b", re.IGNORECASE), "Associate"),
    ]

    def parse(self, job_input: JobCreate) -> JobParsed:
        """
        Parses a JobCreate payload and returns an enriched JobParsed model.
        """
        cleaned_text = TextSanitizer.clean(job_input.description)
        sections = self._segment_job_sections(cleaned_text)

        # 1. Extract skills per section
        required_text = sections.get(JobSectionType.REQUIRED, "")
        preferred_text = sections.get(JobSectionType.PREFERRED, "")
        resp_text = sections.get(JobSectionType.RESPONSIBILITIES, "")

        preferred_skills: set[str] = set()
        if preferred_text:
            pref_detected = skill_extractor_service.extract_from_text(preferred_text)
            preferred_skills = {s.canonical_name for s in pref_detected}

        required_skills: set[str] = set()
        if required_text:
            req_detected = skill_extractor_service.extract_from_text(required_text)
            required_skills = {s.canonical_name for s in req_detected}
        else:
            # Fallback if no explicit "Required" header exists: scan entire text
            all_detected = skill_extractor_service.extract_from_text(cleaned_text)
            required_skills = {
                s.canonical_name for s in all_detected if s.canonical_name not in preferred_skills
            }

        # Ensure preferred and required are disjoint sets
        preferred_skills = preferred_skills - required_skills

        # 2. Extract experience requirement
        min_experience = self._extract_min_experience(cleaned_text)

        # 3. Extract minimum education level
        min_education = self._extract_min_education(cleaned_text)

        # 4. Extract bulleted responsibilities
        responsibilities = self._extract_bullet_items(resp_text)

        # 5. Extract domain keywords
        all_skills = sorted(required_skills | preferred_skills)

        requirements = JobRequirements(
            required_skills=sorted(required_skills),
            preferred_skills=sorted(preferred_skills),
            min_experience_years=min_experience,
            min_education_level=min_education,
            responsibilities=responsibilities,
            domain_keywords=all_skills,
        )

        logger.info(
            "Parsed job '%s': RequiredSkills=%d, PreferredSkills=%d, MinExp=%.1f, MinEdu=%s",
            job_input.title,
            len(required_skills),
            len(preferred_skills),
            min_experience,
            min_education or "None",
        )

        return JobParsed(
            title=job_input.title,
            company=job_input.company,
            location=job_input.location,
            is_remote=job_input.is_remote,
            raw_description=job_input.description,
            cleaned_description=cleaned_text,
            requirements=requirements,
            total_skills_detected=len(all_skills),
        )

    def _segment_job_sections(self, text: str) -> dict[JobSectionType, str]:
        """Splits job text into functional sections."""
        lines = [line.strip() for line in text.split("\n")]
        sections: dict[JobSectionType, list[str]] = {}
        current_section = JobSectionType.UNKNOWN

        for line in lines:
            if not line:
                continue

            detected = self._match_section_header(line)
            if detected is not None:
                current_section = detected
                if current_section not in sections:
                    sections[current_section] = []
            else:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(line)

        return {
            sec_type: "\n".join(content).strip()
            for sec_type, content in sections.items()
            if content
        }

    def _match_section_header(self, line: str) -> JobSectionType | None:
        """Determines if a line acts as a job section header."""
        clean = re.sub(r"^[0-9#*•\-–—.\s]+", "", line).strip().rstrip(":")
        if len(clean) > 50 or not clean:
            return None

        normalized = clean.lower()
        # 1. First pass: exact matches across all section types
        for sec_type, aliases in self.SECTION_HEADER_MAP.items():
            for alias in aliases:
                if normalized == alias:
                    return sec_type

        # 2. Second pass: prefix / suffix match (evaluate preferred and responsibilities before generic required)
        for sec_type in [
            JobSectionType.PREFERRED,
            JobSectionType.RESPONSIBILITIES,
            JobSectionType.REQUIRED,
        ]:
            aliases = self.SECTION_HEADER_MAP[sec_type]
            for alias in aliases:
                if normalized.startswith(f"{alias} ") or normalized.endswith(f" {alias}"):
                    return sec_type

        return None

    def _extract_min_experience(self, text: str) -> float:
        """Extracts minimum years of required experience."""
        for pattern in self.EXP_REQ_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    years = float(match.group(1))
                    if 0.0 <= years <= 30.0:
                        return years
                except (ValueError, IndexError):
                    continue
        return 0.0

    def _extract_min_education(self, text: str) -> str | None:
        """
        Detects lowest required educational degree mentioned.
        If both Bachelor's and Master's are mentioned (e.g. 'Bachelor's or Master's'),
        Bachelor's is chosen as the minimum entry bar.
        """
        found_degrees: list[str] = []
        for pattern, degree_name in self.EDUCATION_HIERARCHY:
            if pattern.search(text):
                found_degrees.append(degree_name)

        if not found_degrees:
            return None

        # Hierarchy priority order (lowest degree represents the minimum required threshold)
        priority_order = ["Associate", "Bachelor's", "Master's", "Ph.D."]
        for deg in priority_order:
            if deg in found_degrees:
                return deg

        return found_degrees[0]

    @staticmethod
    def _extract_bullet_items(section_text: str) -> list[str]:
        """Extracts individual bullet points from a section."""
        if not section_text:
            return []

        bullets: list[str] = []
        for line in section_text.split("\n"):
            clean = line.strip()
            if clean.startswith(("*", "-", "•")):
                clean = clean.lstrip("*-•").strip()
            if len(clean) > 10:
                bullets.append(clean)
        return bullets


# Singleton instance
job_parser_service = JobParserService()
