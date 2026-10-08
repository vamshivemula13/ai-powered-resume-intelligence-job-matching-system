"""
FastAPI Application Entry Point & Lifespan Configuration.

Configures ASGI middleware, global exception handlers,
API route registration, and database initialization lifecycle.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.jobs import router as jobs_router
from app.api.routes.matching import router as matching_router
from app.api.routes.reports import router as reports_router
from app.api.routes.resume import router as resume_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.database.database import init_db

setup_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Runs database schema initialization on startup.
    """
    logger.info("Starting up %s (Env: %s)...", settings.project_name, settings.environment)
    try:
        await init_db()
    except Exception as exc:
        logger.error("Database initialization failed during startup: %s", exc)

    yield

    logger.info("Shutting down %s...", settings.project_name)


app = FastAPI(
    title=settings.project_name,
    description=(
        "Production-quality AI-Powered Recruitment Intelligence System.\n\n"
        "Features:\n"
        "* **PDF Resume Extraction:** PyMuPDF layout parsing and text sanitization.\n"
        "* **Skill Taxonomy Engine:** Configurable canonical skills and alias mapping.\n"
        "* **Job Description Parsing:** Required vs. preferred qualification isolation.\n"
        "* **Multi-Factor Matching:** Configurable scoring (skills, semantics, tenure, education, projects).\n"
        "* **ATS Compliance Audit:** 10-point heuristic evaluating format and readability.\n"
        "* **Candidate Ranking:** Multi-resume comparative leaderboard with explainable insights."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware (Permit all for dev and preview environments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def domain_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Translates custom domain exceptions to structured JSON responses."""
    status_code_map = {
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "ENTITY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PDF_PROCESSING_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "TAXONOMY_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "MODEL_INFERENCE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    http_code = status_code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(status_code=http_code, content=exc.to_dict())


# Register API v1 Routers
app.include_router(resume_router, prefix=settings.api_v1_str)
app.include_router(jobs_router, prefix=settings.api_v1_str)
app.include_router(matching_router, prefix=settings.api_v1_str)
app.include_router(reports_router, prefix=settings.api_v1_str)


@app.get("/", summary="Root index overview")
async def root_index():
    """Provides system overview and links to OpenAPI documentation."""
    return {
        "system": settings.project_name,
        "environment": settings.environment,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_v1_prefix": settings.api_v1_str,
        "status": "operational",
    }
