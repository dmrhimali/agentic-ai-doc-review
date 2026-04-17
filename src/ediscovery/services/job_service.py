"""Job lifecycle management service."""

import json
import logging

from sqlalchemy.orm import Session

from ediscovery.agents.orchestrator import Orchestrator
from ediscovery.models.job import Job
from ediscovery.models.result import ReviewResult
from ediscovery.services.document_service import load_documents_from_directory

logger = logging.getLogger(__name__)


def create_job(
    db: Session,
    job_type: str,
    criteria: dict[str, object],
) -> Job:
    """Create a new job record.

    Args:
        db: Database session.
        job_type: Type of job (e.g. 'relevancy_review').
        criteria: Job-specific criteria as a dict.

    Returns:
        The created Job record.
    """
    job = Job(
        job_type=job_type,
        criteria=json.dumps(criteria),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Created job %s (type=%s)", job.id, job_type)
    return job


def get_job(db: Session, job_id: str) -> Job | None:
    """Get a job by ID.

    Args:
        db: Database session.
        job_id: UUID of the job.

    Returns:
        Job if found, None otherwise.
    """
    return db.query(Job).filter(Job.id == job_id).first()


def list_jobs(db: Session) -> list[Job]:
    """List all jobs ordered by creation time.

    Args:
        db: Database session.

    Returns:
        List of all Job records.
    """
    return (
        db.query(Job).order_by(Job.created_at.desc()).all()
    )


def run_job(db: Session, job_id: str) -> Job:
    """Trigger job execution via the orchestrator.

    Args:
        db: Database session.
        job_id: UUID of the job to run.

    Returns:
        The updated Job record after execution.

    Raises:
        ValueError: If the job is not found.
    """
    job = get_job(db, job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")

    orchestrator = Orchestrator()
    orchestrator.run_job(job_id, db)

    db.refresh(job)
    return job


def create_and_run_job(
    db: Session,
    job_type: str,
    criteria: dict[str, object],
    document_directory: str,
) -> Job:
    """Create a job, load documents from a local directory, and run it.

    Args:
        db: Database session.
        job_type: Type of job (e.g. 'relevancy_review').
        criteria: Job-specific criteria as a dict.
        document_directory: Path to local directory containing documents.

    Returns:
        The completed Job record.

    Raises:
        ValueError: If the directory is invalid or contains no supported files.
    """
    job = create_job(db, job_type, criteria)
    docs = load_documents_from_directory(db, job.id, document_directory)

    if not docs:
        raise ValueError(
            f"No supported documents found in: {document_directory}"
        )

    logger.info(
        "Loaded %d documents from %s for job %s",
        len(docs),
        document_directory,
        job.id,
    )

    orchestrator = Orchestrator()
    orchestrator.run_job(job.id, db)

    db.refresh(job)
    return job


def get_job_results(
    db: Session, job_id: str
) -> list[ReviewResult]:
    """Get all results for a job.

    Args:
        db: Database session.
        job_id: UUID of the job.

    Returns:
        List of ReviewResult records.
    """
    return (
        db.query(ReviewResult)
        .filter(ReviewResult.job_id == job_id)
        .all()
    )
