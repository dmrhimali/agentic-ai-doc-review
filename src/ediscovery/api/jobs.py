"""Job management API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from openai import APIError, AuthenticationError
from sqlalchemy.orm import Session

from ediscovery.database import get_db
from ediscovery.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
)
from ediscovery.schemas.job import (
    JobCreate,
    JobCreateFromDirectory,
    JobListResponse,
    JobResponse,
)
from ediscovery.services import document_service, job_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=201)
def create_job(
    body: JobCreate, db: Session = Depends(get_db)
) -> JobResponse:
    """Create a new review job."""
    job = job_service.create_job(
        db=db,
        job_type=body.job_type,
        criteria=body.criteria,
    )
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
) -> JobListResponse:
    """List all jobs."""
    jobs = job_service.list_jobs(db)
    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str, db: Session = Depends(get_db)
) -> JobResponse:
    """Get a job by ID."""
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post(
    "/{job_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
)
def upload_documents(
    job_id: str,
    files: list[UploadFile],
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload documents to a job."""
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        docs = document_service.save_uploaded_documents(
            db=db, job_id=job_id, files=files
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return DocumentUploadResponse(
        job_id=job_id,
        uploaded=len(docs),
        documents=[
            DocumentResponse.model_validate(d) for d in docs
        ],
    )


@router.post("/{job_id}/run", response_model=JobResponse)
def run_job(
    job_id: str, db: Session = Depends(get_db)
) -> JobResponse:
    """Trigger job execution."""
    try:
        job = job_service.run_job(db, job_id)
    except AuthenticationError as e:
        logger.error("OpenAI authentication failed: %s", e)
        raise HTTPException(
            status_code=401,
            detail="OpenAI API key is invalid or missing",
        ) from e
    except (APIError, RuntimeError) as e:
        logger.error("Job execution error: %s", e)
        raise HTTPException(
            status_code=502, detail=f"LLM service error: {e}"
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return JobResponse.model_validate(job)


@router.post(
    "/run-directory",
    response_model=JobResponse,
    status_code=201,
)
def create_and_run_from_directory(
    body: JobCreateFromDirectory,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Create a job from a local directory and run it immediately."""
    try:
        job = job_service.create_and_run_job(
            db=db,
            job_type=body.job_type,
            criteria=body.criteria,
            document_directory=body.document_directory,
        )
    except AuthenticationError as e:
        logger.error("OpenAI authentication failed: %s", e)
        raise HTTPException(
            status_code=401,
            detail="OpenAI API key is invalid or missing",
        ) from e
    except (APIError, RuntimeError) as e:
        logger.error("Job execution error: %s", e)
        raise HTTPException(
            status_code=502, detail=f"LLM service error: {e}"
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return JobResponse.model_validate(job)
