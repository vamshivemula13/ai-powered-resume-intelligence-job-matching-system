"""
Command-Line Interface (CLI) Runner.

Usage:
    python -m app.cli analyze-resume <resume.pdf|resume.txt> <job.txt>
    python -m app.cli audit-ats <resume.pdf|resume.txt>
"""

import argparse
import sys
from pathlib import Path

from app.core.exceptions import AppException
from app.schemas.job import JobCreate
from app.schemas.match import SkillMatchStatus
from app.services.ats_service import ats_service
from app.services.job_parser import job_parser_service
from app.services.matching_service import matching_service
from app.services.pdf_service import ExtractedDocument, pdf_extractor


def load_resume_document(path_str: str) -> ExtractedDocument:
    """Loads and sanitizes resume from PDF or plain text file."""
    path = Path(path_str)
    if not path.exists():
        print(f"Error: Resume file not found at '{path}'", file=sys.stderr)
        sys.exit(1)

    if path.suffix.lower() == ".pdf":
        return pdf_extractor.extract(path)

    # Plain text file
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    return ExtractedDocument(
        raw_text=text,
        cleaned_text=text.strip(),
        total_pages=1,
        character_count=len(text),
        word_count=len(text.split()),
    )


def load_job_text(path_str: str) -> str:
    """Loads job description text from file."""
    path = Path(path_str)
    if not path.exists():
        print(f"Error: Job description file not found at '{path}'", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def cmd_analyze_resume(resume_path: str, job_path: str) -> None:
    """Runs end-to-end match analysis and prints formatted report."""
    from app.services.resume_parser import resume_parser_service

    doc = load_resume_document(resume_path)
    resume = resume_parser_service.parse(doc, filename=Path(resume_path).name)

    job_text = load_job_text(job_path)
    job_input = JobCreate(title="Target Position", description=job_text)
    job = job_parser_service.parse(job_input)

    report = matching_service.analyze_match(resume, job)

    cand_name = resume.candidate_profile.contact.full_name or "Candidate"

    print("\n" + "=" * 50)
    print("      RESUME INTELLIGENCE REPORT")
    print("=" * 50)
    print(f"Candidate: {cand_name}")
    print(f"Position : {job.title}")
    print(f"\nOverall Match Score: {report.overall_score}%")
    print("-" * 50)
    print(f"• Skill Match       : {report.breakdown.skill_score}%")
    print(f"• Semantic Match    : {report.breakdown.semantic_score}%")
    print(f"• Experience Match  : {report.breakdown.experience_score}%")
    print(f"• Education Match   : {report.breakdown.education_score}%")
    print(f"• Project Match     : {report.breakdown.project_score}%")
    print(f"• ATS Health Score  : {report.ats_analysis.ats_score}%")
    print("-" * 50)

    print("\nTechnical Skill Alignment:")
    for gap in report.skill_gap:
        if gap.status == SkillMatchStatus.STRONG_MATCH:
            icon = "✓"
        elif gap.status == SkillMatchStatus.PARTIAL_MATCH:
            icon = "⚠"
        else:
            icon = "✗"
        print(f"  {icon} {gap.skill_name:<20} [{gap.status.value}] ({gap.priority.value})")

    if report.missing_critical_skills:
        print("\nMissing Critical Skills:")
        for idx, missing in enumerate(report.missing_critical_skills, start=1):
            print(f"  {idx}. {missing}")

    if report.strengths:
        print("\nKey Strengths:")
        for s in report.strengths:
            print(f"  + {s}")

    if report.recommendations:
        print("\nActionable Recommendations:")
        for r in report.recommendations:
            print(f"  - {r}")

    print("=" * 50 + "\n")


def cmd_audit_ats(resume_path: str) -> None:
    """Runs ATS audit on a resume and displays checklist."""
    from app.services.resume_parser import resume_parser_service

    doc = load_resume_document(resume_path)
    resume = resume_parser_service.parse(doc, filename=Path(resume_path).name)
    report = ats_service.analyze(resume)

    print("\n" + "=" * 50)
    print("      ATS COMPLIANCE AUDIT")
    print("=" * 50)
    print(f"Candidate: {resume.candidate_profile.contact.full_name or 'Unknown'}")
    print(f"ATS Score: {report.ats_score} / 100")
    print("-" * 50)

    print("Checklist:")
    for item in report.checklist:
        status_icon = "✓" if item.passed else "✗"
        print(f"  {status_icon} {item.criterion:<22}: {item.message}")

    if report.improvements:
        print("\nImprovement Recommendations:")
        for imp in report.improvements:
            print(f"  {imp}")

    print("=" * 50 + "\n")


def main() -> None:
    """CLI argument dispatcher."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Resume Intelligence & Job Matching CLI",
        prog="python -m app.cli",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze-resume
    p_analyze = subparsers.add_parser("analyze-resume", help="Match resume against a job")
    p_analyze.add_argument("resume", help="Path to resume PDF or TXT")
    p_analyze.add_argument("job", help="Path to job description TXT")

    # audit-ats
    p_audit = subparsers.add_parser("audit-ats", help="Evaluate ATS readability of a resume")
    p_audit.add_argument("resume", help="Path to resume PDF or TXT")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "analyze-resume":
            cmd_analyze_resume(args.resume, args.job)
        elif args.command == "audit-ats":
            cmd_audit_ats(args.resume)
    except AppException as exc:
        print(f"Application Error [{exc.code}]: {exc.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
