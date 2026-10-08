"""
ATS (Applicant Tracking System) Compliance Analyzer Service.

Evaluates resume readability, structural completeness, contact availability,
and formatting adherence against heuristic ATS standards.
"""

from app.schemas.match import ATSCheckItem, ATSReport
from app.schemas.resume import ParsedResume, ResumeSectionType


class ATSService:
    """
    Evaluates resumes against 10 ATS-style criteria and calculates a 0-100 score.
    """

    def analyze(self, resume: ParsedResume) -> ATSReport:
        """
        Runs comprehensive ATS heuristic checks on a parsed resume.
        """
        checklist: list[ATSCheckItem] = []
        passed_checks: list[str] = []
        improvements: list[str] = []
        score = 0.0

        contact = resume.candidate_profile.contact

        # 1. Full Name
        if contact.full_name and len(contact.full_name.split()) >= 2:
            score += 10.0
            msg = f"Candidate name detected: {contact.full_name}"
            checklist.append(ATSCheckItem(criterion="Candidate Name", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(
                    criterion="Candidate Name",
                    passed=False,
                    message="Full name not distinctly identified at document top",
                )
            )
            improvements.append("⚠ Ensure your full name appears prominently at the top of your resume")

        # 2. Email Address
        if contact.email:
            score += 10.0
            msg = f"Valid email detected: {contact.email}"
            checklist.append(ATSCheckItem(criterion="Email Address", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(criterion="Email Address", passed=False, message="No valid email found")
            )
            improvements.append("⚠ Add a professional email address in the contact section")

        # 3. Phone Number
        if contact.phone:
            score += 10.0
            msg = f"Phone contact detected: {contact.phone}"
            checklist.append(ATSCheckItem(criterion="Phone Number", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(criterion="Phone Number", passed=False, message="No phone number detected")
            )
            improvements.append("⚠ Add a direct contact phone number with country/area code")

        # 4. Professional Footprint (LinkedIn / GitHub)
        if contact.linkedin_url or contact.github_url:
            score += 5.0
            links = [u for u in (contact.linkedin_url, contact.github_url) if u]
            msg = f"Professional profile linked: {', '.join(links)}"
            checklist.append(ATSCheckItem(criterion="Online Footprint", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(
                    criterion="Online Footprint",
                    passed=False,
                    message="No LinkedIn or GitHub profile link found",
                )
            )
            improvements.append("⚠ Include a LinkedIn or GitHub profile link for recruiter verification")

        # 5. Work Experience Section
        if ResumeSectionType.EXPERIENCE in resume.sections and len(resume.sections[ResumeSectionType.EXPERIENCE]) > 50:
            score += 15.0
            msg = "Standard 'Experience' section detected with substantial content"
            checklist.append(ATSCheckItem(criterion="Experience Section", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(
                    criterion="Experience Section",
                    passed=False,
                    message="Missing or sparse work experience section",
                )
            )
            improvements.append("⚠ Structure work history under a standard 'Work Experience' header")

        # 6. Technical Skills Section
        if ResumeSectionType.SKILLS in resume.sections and len(resume.sections[ResumeSectionType.SKILLS]) > 20:
            score += 15.0
            msg = "Dedicated 'Technical Skills' section detected"
            checklist.append(ATSCheckItem(criterion="Skills Section", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(
                    criterion="Skills Section",
                    passed=False,
                    message="Missing dedicated skills section",
                )
            )
            improvements.append("⚠ Create a standalone 'Technical Skills' section with categorizations")

        # 7. Education Section
        if (
            ResumeSectionType.EDUCATION in resume.sections
            or len(resume.candidate_profile.education_entries) > 0
        ):
            score += 10.0
            msg = "Recognizable 'Education' qualifications detected"
            checklist.append(ATSCheckItem(criterion="Education Section", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(criterion="Education Section", passed=False, message="No education section found")
            )
            improvements.append("⚠ Add an 'Education' section detailing degrees and graduation years")

        # 8. Summary / Objective
        if ResumeSectionType.SUMMARY in resume.sections:
            score += 5.0
            msg = "Professional summary / executive overview section present"
            checklist.append(ATSCheckItem(criterion="Professional Summary", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(criterion="Professional Summary", passed=False, message="Summary omitted")
            )
            improvements.append("⚠ Consider adding a 2-3 sentence 'Professional Summary' at the top")

        # 9. Document Word Count & Content Depth
        word_count = len(resume.cleaned_text.split())
        if 150 <= word_count <= 2500:
            score += 10.0
            msg = f"Ideal content length: {word_count} words ({resume.total_pages} pages)"
            checklist.append(ATSCheckItem(criterion="Content Length", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(
                    criterion="Content Length",
                    passed=False,
                    message=f"Word count ({word_count}) is too brief or excessive",
                )
            )
            improvements.append(f"⚠ Maintain a standard resume length of 300-1000 words (current: {word_count})")

        # 10. Document Extractability (Not Scanned / Not Image-Only)
        if not resume.is_scanned:
            score += 10.0
            msg = "Text is digitally encoded and cleanly indexable by ATS parsers"
            checklist.append(ATSCheckItem(criterion="Machine Readability", passed=True, message=msg))
            passed_checks.append(f"✓ {msg}")
        else:
            checklist.append(
                ATSCheckItem(
                    criterion="Machine Readability",
                    passed=False,
                    message="Document appears scanned or image-based",
                )
            )
            improvements.append("⚠ Avoid scanned images; export your resume directly as a selectable text PDF")

        return ATSReport(
            ats_score=round(min(score, 100.0), 1),
            passed_checks=passed_checks,
            improvements=improvements,
            checklist=checklist,
        )


# Singleton ATS service
ats_service = ATSService()
