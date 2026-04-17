"""Orchestrator agent — supervises job execution pipeline."""

import datetime
import json
import logging

from sqlalchemy.orm import Session

from review.agents.base import (
    JobWorker,
    OrchestratorContext,
    WorkerResult,
)
from review.agents.registry import JobTypeRegistry
from review.config import get_model_config
from review.extraction.extractor import extract_text
from review.models.job import Job, JobDocument
from review.models.prompt import PromptTemplate
from review.models.result import ReviewResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """Supervisor agent that plans, delegates, and aggregates job results.

    The orchestrator:
    1. Loads job metadata, documents, and prompts from the database.
    2. Resolves the appropriate worker from the registry.
    3. For each document: extracts text, delegates to worker,
       runs quality check, and persists results.
    4. Updates job status throughout the pipeline.
    """

    def run_job(self, job_id: str, db: Session) -> None:
        """Execute a complete job pipeline.

        Args:
            job_id: UUID of the job to execute.
            db: Database session.

        Raises:
            ValueError: If the job is not found or not in pending state.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        if job.status != "pending":
            raise ValueError(
                f"Job {job_id} is in '{job.status}' state, "
                f"expected 'pending'"
            )

        logger.info("Starting job %s (type=%s)", job_id, job.job_type)

        job.status = "running"
        job.started_at = datetime.datetime.utcnow()
        db.commit()

        try:
            model_config = get_model_config(job.job_type)
            context = self._build_context(job, db, model_config.model)
            worker = JobTypeRegistry.get_worker(
                job.job_type, model_config
            )

            documents = (
                db.query(JobDocument)
                .filter(JobDocument.job_id == job_id)
                .all()
            )
            job.total_documents = len(documents)
            db.commit()

            for doc in documents:
                self._process_document(
                    doc, worker, context, db
                )
                job.processed_documents += 1
                db.commit()

            if context.errors:
                job.status = "completed_with_errors"
                logger.warning(
                    "Job %s completed with %d document errors: %s",
                    job_id,
                    len(context.errors),
                    "; ".join(context.errors),
                )
            else:
                job.status = "completed"
                logger.info(
                    "Job %s completed successfully (%d documents)",
                    job_id,
                    job.total_documents,
                )
            job.completed_at = datetime.datetime.utcnow()
            db.commit()

        except Exception:
            logger.exception("Job %s failed", job_id)
            job.status = "failed"
            job.completed_at = datetime.datetime.utcnow()
            db.commit()
            raise

    def _build_context(
        self, job: Job, db: Session, model_used: str
    ) -> OrchestratorContext:
        """Build orchestration context from job and database state."""
        criteria = json.loads(job.criteria)

        prompts_rows = (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.job_type == job.job_type,
                PromptTemplate.is_active.is_(True),
            )
            .all()
        )
        prompts = {row.name: row.content for row in prompts_rows}

        return OrchestratorContext(
            job_id=job.id,
            job_type=job.job_type,
            criteria=criteria,
            prompts=prompts,
            model_used=model_used,
        )

    def _process_document(
        self,
        doc: JobDocument,
        worker: JobWorker,
        context: OrchestratorContext,
        db: Session,
    ) -> None:
        """Process a single document through the worker pipeline."""
        logger.info(
            "Processing document %s (%s)", doc.id, doc.filename
        )
        doc.status = "processing"
        db.commit()

        try:
            if not doc.extracted_text:
                doc.extracted_text = extract_text(doc.file_path)
                db.commit()

            result = worker.process_document(
                document_text=doc.extracted_text,
                criteria=context.criteria,
                prompts=context.prompts,
            )

            qc_result = worker.quality_check(
                document_text=doc.extracted_text,
                initial_result=result,
                criteria=context.criteria,
                prompts=context.prompts,
            )

            final_result: WorkerResult
            if qc_result.is_approved:
                final_result = result
            else:
                final_result = (
                    qc_result.revised_result
                    if qc_result.revised_result
                    else result
                )
                logger.info(
                    "QC revised result for doc %s: %s",
                    doc.id,
                    qc_result.reason,
                )

            review_result = ReviewResult(
                job_id=context.job_id,
                document_id=doc.id,
                job_type=context.job_type,
                result=json.dumps(final_result.result_data),
                confidence=final_result.confidence,
                explanation=final_result.explanation,
                model_used=context.model_used,
                prompt_tokens=final_result.prompt_tokens,
                completion_tokens=final_result.completion_tokens,
            )
            db.add(review_result)

            doc.status = "completed"
            db.commit()

        except Exception:
            logger.exception(
                "Failed to process document %s", doc.id
            )
            doc.status = "failed"
            db.commit()
            context.errors.append(
                f"Document {doc.id} ({doc.filename}) failed"
            )
