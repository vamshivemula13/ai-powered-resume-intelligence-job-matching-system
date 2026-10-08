"""
Resume Parsing and Section Segmentation Service.

Deconstructs raw extracted document text into standardized sections,
extracts candidate contact details, detects educational history,
and estimates total years of professional experience.
"""

import re
from datetime import datetime

from app.core.logging import get_logger
from app.schemas.candidate import CandidateProfile, ContactInfo, EducationEntry
from app.schemas.resume import ParsedResume, ResumeSectionType
from app.services.pdf_service import ExtractedDocument

logger = get_logger(__name__)


class ResumeParserService:
    """
    Parses unstructured resume text into a structured, categorized representation.
    Designed to tolerate diverse formats, bullet styles, and header aliases.
    """

    # Section aliases mapped to standard Section Types
    SECTION_HEADER_MAP: dict[ResumeSectionType, list[str]] = {
        ResumeSectionType.SUMMARY: [
            "summary",
            "professional summary",
            "career summary",
            "profile",
            "professional profile",
            "about me",
            "overview",
            "career objective",
            "objective",
        ],
        ResumeSectionType.SKILLS: [
            "skills",
            "technical skills",
            "core competencies",
            "competencies",
            "technologies",
            "tools & technologies",
            "tools and technologies",
            "key skills",
            "technical proficiencies",
            "areas of expertise",
        ],
        ResumeSectionType.EXPERIENCE: [
            "experience",
            "work experience",
            "professional experience",
            "employment history",
            "work history",
            "career history",
            "relevant experience",
            "employment",
        ],
        ResumeSectionType.EDUCATION: [
            "education",
            "academic background",
            "academics",
            "qualifications",
            "educational background",
            "degrees",
        ],
        ResumeSectionType.PROJECTS: [
            "projects",
            "key projects",
            "personal projects",
            "notable projects",
            "academic projects",
            "technical projects",
        ],
        ResumeSectionType.CERTIFICATIONS: [
            "certifications",
            "licenses & certifications",
            "licenses and certifications",
            "courses & certifications",
            "credentials",
            "certifications and licenses",
        ],
        ResumeSectionType.ACHIEVEMENTS: [
            "achievements",
            "honors & awards",
            "honors and awards",
            "awards",
            "accomplishments",
        ],
    }

    # Regex patterns for contact information
    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE
    )
    PHONE_REGEX = re.compile(
        r"(?:(?:\+|00)?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}",
    )
    LINKEDIN_REGEX = re.compile(
        r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)", re.IGNORECASE
    )
    GITHUB_REGEX = re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE
    )

    # Degree recognition patterns
    DEGREE_PATTERNS = [
        (re.compile(r"\b(Ph\.?D\.?|Doctor of Philosophy|Doctorate)\b", re.IGNORECASE), "Ph.D."),
        (re.compile(r"\b(M\.?S\.?|Master of Science|Master's|M\.?Tech|MBA)\b", re.IGNORECASE), "Master's"),
        (re.compile(r"\b(B\.?S\.?|Bachelor of Science|Bachelor's|B\.?Tech|B\.?E\.?|B\.?A\.?)\b", re.IGNORECASE), "Bachelor's"),
        (re.compile(r"\b(Associate of Science|Associate Degree|A\.?S\.?)\b", re.IGNORECASE), "Associate"),
    ]

    # Year range pattern for calculating experience spans (e.g. 2018 - 2023 or 2020 - Present)
    YEAR_RANGE_REGEX = re.compile(
        r"\b(19\d{2}|20\d{2})\s*(?:[-–—]|to)\s*(19\d{2}|20\d{2}|present|current)\b",
        re.IGNORECASE,
    )
    EXPLICIT_EXP_REGEX = re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\b(?:\s*of)?\s*(?:experience|exp)?",
        re.IGNORECASE,
    )

    def parse(self, document: ExtractedDocument, filename: str = "resume.pdf") -> ParsedResume:
        """
        Deconstructs an ExtractedDocument into structured sections and candidate profile.
        """
        text = document.cleaned_text
        sections = self._segment_sections(text)
        contact_info = self._extract_contact_info(text)
        education_entries = self._extract_education(sections.get(ResumeSectionType.EDUCATION, text))
        experience_years = self._estimate_experience_years(
            sections.get(ResumeSectionType.EXPERIENCE, text), text
        )

        # Summary text from explicit section, or first 300 characters fallback
        summary_text = sections.get(ResumeSectionType.SUMMARY)

        profile = CandidateProfile(
            contact=contact_info,
            summary=summary_text,
            estimated_experience_years=experience_years,
            education_entries=education_entries,
        )

        logger.info(
            "Parsed resume '%s': Sections=%d, Candidate='%s', ExpYears=%.1f",
            filename,
            len(sections),
            contact_info.full_name or "Unknown",
            experience_years,
        )

        return ParsedResume(
            filename=filename,
            total_pages=document.total_pages,
            is_scanned=document.is_scanned,
            candidate_profile=profile,
            sections=sections,
            raw_text=document.raw_text,
            cleaned_text=document.cleaned_text,
        )

    def _segment_sections(self, text: str) -> dict[ResumeSectionType, str]:
        """
        Segments raw lines into semantic sections using header alias matching.
        """
        lines = [line.strip() for line in text.split("\n")]
        sections: dict[ResumeSectionType, list[str]] = {}
        current_section: ResumeSectionType = ResumeSectionType.UNKNOWN

        for line in lines:
            if not line:
                continue

            detected_type = self._match_section_header(line)
            if detected_type is not None:
                current_section = detected_type
                if current_section not in sections:
                    sections[current_section] = []
            else:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(line)

        # Join line lists into contiguous section text
        return {
            sec_type: "\n".join(content_lines).strip()
            for sec_type, content_lines in sections.items()
            if content_lines
        }

    def _match_section_header(self, line: str) -> ResumeSectionType | None:
        """
        Determines whether a line is a section header.
        Headers are typically short (<= 50 chars), capitalized or suffixed with colons.
        """
        # Clean line of decorative characters, bullets, and numbering
        clean_line = re.sub(r"^[0-9#*•\-–—.\s]+", "", line).strip()
        clean_line = clean_line.rstrip(":")

        # Ignore long sentences or paragraph lines
        if len(clean_line) > 50 or not clean_line:
            return None

        normalized = clean_line.lower()

        for sec_type, aliases in self.SECTION_HEADER_MAP.items():
            for alias in aliases:
                # Exact match or wrapped in decorative formatting
                if normalized == alias or normalized.startswith(f"{alias} ") or normalized.endswith(f" {alias}"):
                    return sec_type

        return None

    def _extract_contact_info(self, text: str) -> ContactInfo:
        """Extracts email, phone, social links, and candidate full name."""
        email_match = self.EMAIL_REGEX.search(text)
        email = email_match.group(0) if email_match else None

        phone: str | None = None
        for phone_cand in self.PHONE_REGEX.finditer(text):
            cand_str = phone_cand.group(0).strip()
            digits_only = re.sub(r"\D", "", cand_str)
            if 7 <= len(digits_only) <= 15:
                phone = cand_str
                break

        linkedin_match = self.LINKEDIN_REGEX.search(text)
        linkedin_url = (
            f"https://linkedin.com/in/{linkedin_match.group(1)}"
            if linkedin_match
            else None
        )

        github_match = self.GITHUB_REGEX.search(text)
        github_url = (
            f"https://github.com/{github_match.group(1)}"
            if github_match
            else None
        )

        full_name = self._extract_candidate_name(text)

        return ContactInfo(
            full_name=full_name,
            email=email,
            phone=phone,
            linkedin_url=linkedin_url,
            github_url=github_url,
        )

    def _extract_candidate_name(self, text: str) -> str | None:
        """
        Heuristic name extractor:
        Inspects the first few lines of text. The candidate's name is typically
        at the top, 2 to 4 words, free of email addresses, digits, and urls.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            # Skip lines with obvious non-name content
            if (
                "@" in line
                or "http" in line
                or "github" in line.lower()
                or "linkedin" in line.lower()
                or any(char.isdigit() for char in line)
            ):
                continue

            words = line.split()
            # Most human names on resumes are 2 to 4 capitalized words
            if 2 <= len(words) <= 4:
                # Disallow section headers masquerading as names
                if self._match_section_header(line) is None:
                    return line

        return None

    def _extract_education(self, edu_text: str) -> list[EducationEntry]:
        """Detects degrees, graduation years, and educational qualifications across adjacent lines."""
        entries: list[EducationEntry] = []
        lines = [line.strip() for line in edu_text.split("\n") if line.strip()]

        for i, line_str in enumerate(lines):
            for pattern, canonical_degree in self.DEGREE_PATTERNS:
                if pattern.search(line_str):
                    # Check current line and adjacent line for graduation year
                    context_chunk = line_str
                    if i + 1 < len(lines):
                        context_chunk += " " + lines[i + 1]

                    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", context_chunk)
                    grad_year = int(year_match.group(1)) if year_match else None

                    # If next line exists and doesn't match a new degree, use it as institution
                    institution = line_str[:80]
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        is_next_another_degree = any(p.search(next_line) for p, _ in self.DEGREE_PATTERNS)
                        if not is_next_another_degree:
                            institution = next_line[:80]

                    entries.append(
                        EducationEntry(
                            degree=canonical_degree,
                            institution=institution,
                            year=grad_year,
                        )
                    )
                    break

        return entries

    def _estimate_experience_years(self, exp_text: str, full_text: str) -> float:
        """
        Estimates total years of professional experience using date intervals
        and explicit tenure declarations.
        """
        current_year = datetime.now().year
        total_years = 0.0
        intervals_found = 0

        # Scan date ranges like '2019 - 2023' or '2021 - Present'
        for match in self.YEAR_RANGE_REGEX.finditer(exp_text):
            start_str, end_str = match.group(1), match.group(2).lower()
            start_year = int(start_str)

            if end_str in ("present", "current"):
                end_year = current_year
            else:
                end_year = int(end_str)

            if end_year >= start_year and (end_year - start_year) <= 40:
                total_years += (end_year - start_year)
                intervals_found += 1

        # Fallback: check if the resume explicitly mentions 'X years of experience'
        if total_years == 0.0:
            explicit_match = self.EXPLICIT_EXP_REGEX.search(full_text)
            if explicit_match:
                try:
                    total_years = float(explicit_match.group(1))
                except ValueError:
                    pass

        # Cap experience at a reasonable maximum
        return round(min(total_years, 45.0), 1)


# Singleton parser service
resume_parser_service = ResumeParserService()
