"""Document file handling and storage service."""

import logging
import shutil
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from review.config import settings
from review.extraction.extractor import SUPPORTED_EXTENSIONS
from review.models.job import Job, JobDocument

logger = logging.getLogger(__name__)


def save_uploaded_documents(
    db: Session,
    job_id: str,
    files: list[UploadFile],
) -> list[JobDocument]:
    """Save uploaded files to disk and create DB records.

    Args:
        db: Database session.
        job_id: UUID of the parent job.
        files: List of uploaded file objects.

    Returns:
        List of created JobDocument records.

    Raises:
        ValueError: If the job is not found.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise ValueError(f"Job not found: {job_id}")

    upload_dir = Path(settings.upload_dir) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    documents: list[JobDocument] = []

    for file in files:
        filename = file.filename or "unnamed"
        file_path = upload_dir / filename

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        doc = JobDocument(
            job_id=job_id,
            filename=filename,
            file_path=str(file_path),
        )
        db.add(doc)
        documents.append(doc)
        logger.info(
            "Saved document '%s' for job %s", filename, job_id
        )

    job.total_documents = (
        db.query(JobDocument)
        .filter(JobDocument.job_id == job_id)
        .count()
        + len(documents)
    )
    db.commit()

    for doc in documents:
        db.refresh(doc)

    return documents


def load_documents_from_directory(
    db: Session,
    job_id: str,
    directory: str,
) -> list[JobDocument]:
    """Scan a local directory for supported files and register them.

    Files are referenced in-place (not copied). Only files with
    supported extensions (.pdf, .docx, .txt) are included.

    Args:
        db: Database session.
        job_id: UUID of the parent job.
        directory: Path to the local directory to scan.

    Returns:
        List of created JobDocument records.

    Raises:
        ValueError: If the job is not found or directory is invalid.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise ValueError(f"Job not found: {job_id}")

    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Not a valid directory: {directory}")

    documents: list[JobDocument] = []

    for file_path in sorted(dir_path.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.info(
                "Skipping unsupported file: %s", file_path.name
            )
            continue

        doc = JobDocument(
            job_id=job_id,
            filename=file_path.name,
            file_path=str(file_path.resolve()),
        )
        db.add(doc)
        documents.append(doc)
        logger.info(
            "Registered document '%s' for job %s",
            file_path.name,
            job_id,
        )

    job.total_documents = len(documents)
    db.commit()

    for doc in documents:
        db.refresh(doc)

    return documents
