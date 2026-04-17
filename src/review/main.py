"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import review.agents.entity_extraction  # noqa: F401
import review.agents.relevancy  # noqa: F401
from review.api.jobs import router as jobs_router
from review.api.results import router as results_router
from review.config import settings
from review.database import engine
from review.models.base import Base

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: create tables on startup."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Agentic AI Document Relevance Review",
    description=(
        "Domain-agnostic agentic AI system for document relevance "
        "review. Supports relevancy classification with quality-check "
        "loops and model escalation on low confidence."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(jobs_router)
app.include_router(results_router)


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch unhandled exceptions and return clean JSON."""
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
