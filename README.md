# 🤖 AI-Powered Resume Intelligence & Job Matching System

An enterprise-grade recruitment intelligence and candidate-job matching engine built in **Python 3.10+ / 3.12**, powered by **FastAPI**, **PyMuPDF**, **SQLAlchemy 2.0 Async**, **spaCy**, and **Sentence Transformers**.

Provides multi-dimensional compatibility scoring, dense vector semantic similarity, ATS compliance auditing, transparent skill-gap analysis, and multi-candidate ranking.

---

## 🎯 Problem Statement & Core Value
Traditional Applicant Tracking Systems (ATS) rely on naive keyword counts. This causes:
1. **Semantic Blind Spots:** Candidates describing *"RESTful microservice development in FastAPI"* are filtered out if the job listing asks for *"backend web services"*.
2. **Black-Box Scores:** Arbitrary percentages with no actionable breakdown.
3. **Keyword Stuffing Exploitation:** Low-quality resumes packed with hidden white-font keywords receive falsely inflated scores.
4. **Document Layout Chaos:** Multi-column PDFs often lead to mangled text in standard parsers.

**Our Solution:** A hybrid pipeline combining layout-preserving text extraction, boundary-aware taxonomy matching, dense vector embeddings, and an explainable 5-factor scoring engine.

---

## 🏗️ System Architecture

```
[Candidate PDF Resume]                [Job Description / Requirements]
         │                                            │
         ▼                                            ▼
┌──────────────────┐                         ┌──────────────────┐
│ PDF & Text Layer │                         │ Job Parser Layer │
│  (PyMuPDF/fitz)  │                         │(Pydantic Schema) │
└────────┬─────────┘                         └────────┬─────────┘
         │                                            │
         ▼                                            ▼
┌──────────────────┐                         ┌──────────────────┐
│ Section & Entity │                         │ Extracted Skills │
│  Parser (spaCy)  │                         │ & Requirements   │
└────────┬─────────┘                         └────────┬─────────┘
         │                                            │
         ▼                                            ▼
┌──────────────────┐                         ┌──────────────────┐
│ Skill Extractor  │                         │ Semantic Vector  │
│(Taxonomy Engine) │                         │  Embeddings      │
└────────┬─────────┘                         └────────┬─────────┘
         │                                            │
         └────────────────────┬───────────────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Multi-Factor Match Engine│
                 │ ─────────────────────── │
                 │ • Skill Match    (35%)  │
                 │ • Semantic Vector (25%) │
                 │ • Experience     (20%)  │
                 │ • Education      (10%)  │
                 │ • Projects       (10%)  │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Explainable Match Report│
                 │ • ATS Compliance Score  │
                 │ • Skill Gap Matrix      │
                 │ • Actionable Suggestions│
                 │ • Candidate Ranking     │
                 └─────────────────────────┘
```

---

## 📦 Technology Stack

| Layer | Component | Details |
|---|---|---|
| **Language** | Python 3.10+ / 3.12 | Type hints (PEP 585/604), OOP, dataclasses, asyncio |
| **API Framework** | FastAPI & Uvicorn | Async ASGI server, auto-generated OpenAPI & Swagger UI (`/docs`) |
| **Data Contracts** | Pydantic v2 & Pydantic-Settings | Rust-backed schema validation and `.env` parsing |
| **PDF Extraction** | PyMuPDF (`fitz`) | C-based extraction preserving column bounding blocks |
| **Skill Taxonomy** | JSON Taxonomy (`skills.json`) | Configurable catalog with aliases, boundaries, and categories |
| **Vector Similarity** | Sentence Transformers / Cosine Math | Dense vector contextual semantic comparison |
| **Database & ORM** | PostgreSQL & SQLite / SQLAlchemy 2.0 | Async engine (`asyncpg`, `aiosqlite`) with Repository Pattern |
| **Testing** | pytest & pytest-asyncio | 39 automated unit, integration, and edge-case tests |
| **Code Quality** | Ruff & Black | Deterministic formatting and zero-warning linting |
| **Deployment** | Docker & Docker Compose | Multi-stage image with PostgreSQL container |

---

## ⚖️ Multi-Factor Scoring Engine

The overall compatibility score is computed as a weighted heuristic normalized between 0.0% and 100.0%:

$$\text{Final Score} = (S_{\text{skill}} \times 0.35) + (S_{\text{semantic}} \times 0.25) + (S_{\text{exp}} \times 0.20) + (S_{\text{edu}} \times 0.10) + (S_{\text{proj}} \times 0.10)$$

* **Skill Match (35%):** Prioritizes Required competencies (80% weight) over Preferred/Bonus skills (20% weight).
* **Semantic Match (25%):** Computes cosine similarity of dense vector embeddings.
* **Experience Tenure (20%):** Compares candidate verified years against minimum required tenure.
* **Education Degree (10%):** Evaluates highest degree against required baseline (Ph.D. > Master's > Bachelor's > Associate).
* **Project Alignment (10%):** Measures semantic similarity between portfolio projects and job responsibilities.

---

## 🔍 ATS Compliance Analyzer (10 Criteria)

1. **Candidate Name Identification:** Prominently placed at top.
2. **Email Verification:** Valid RFC-compliant address.
3. **Phone Contact:** Recognizable phone format.
4. **Online Footprint:** Verified LinkedIn or GitHub profile links.
5. **Standard Experience Header:** Work history under recognizable header.
6. **Technical Skills Section:** Categorized technical competencies.
7. **Education Credentials:** Degrees and graduation dates.
8. **Professional Summary:** 2–3 sentence executive overview.
9. **Word Count & Density:** Between 150 and 2,500 words.
10. **Machine Readability:** Digitally encoded selectable text (not scanned images).

---

## 🚀 Quickstart & Commands

### 1. Run Automated Test Suite (39 Tests)
```bash
pytest tests/ -v
```

### 2. Run Ruff Code Linter
```bash
ruff check app tests
```

### 3. Run Command-Line Interface (CLI)
Analyze a resume against a target job description:
```bash
python -m app.cli analyze-resume data/sample_resumes/alex_mercer.txt data/sample_jobs/senior_python_engineer.txt
```

Run an ATS compliance audit:
```bash
python -m app.cli audit-ats data/sample_resumes/alex_mercer.txt
```

### 4. Run FastAPI Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open interactive Swagger UI: **`http://localhost:8000/docs`**

---

## 🌐 Production REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/resumes/upload` | Upload PDF resume, extract text, detect skills, save candidate |
| `POST` | `/api/v1/resumes/parse-text` | Parse raw text resume directly |
| `POST` | `/api/v1/jobs` | Ingest job description, isolate required vs preferred skills |
| `GET` | `/api/v1/jobs` | List paginated job postings |
| `GET` | `/api/v1/jobs/{job_id}` | Get job details and parsed requirements by ID |
| `POST` | `/api/v1/matching/analyze` | Compute 5-factor match score, ATS score, and skill gaps |
| `POST` | `/api/v1/matching/rank` | Rank multiple candidate resumes against a single job |
| `GET` | `/api/v1/health` | System diagnostics, database connection, taxonomy stats |
| `GET` | `/api/v1/taxonomy` | View canonical skill catalog and categories |

---

