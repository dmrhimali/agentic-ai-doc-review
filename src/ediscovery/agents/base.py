"""Base protocol and data structures for job workers."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class WorkerResult:
    """Result returned by a worker agent after processing a document."""

    is_successful: bool
    result_data: dict[str, Any]
    confidence: float
    explanation: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class QualityCheckResult:
    """Result of a quality check on worker output."""

    is_approved: bool
    revised_result: WorkerResult | None = None
    reason: str = ""


@dataclass
class OrchestratorContext:
    """Context passed through the orchestration pipeline."""

    job_id: str
    job_type: str
    criteria: dict[str, Any]
    prompts: dict[str, str]
    model_used: str = ""
    errors: list[str] = field(default_factory=list)


class JobWorker(Protocol):
    """Protocol that all job type workers must implement."""

    @property
    def job_type(self) -> str:
        """Return the job type this worker handles."""
        ...

    def process_document(
        self,
        document_text: str,
        criteria: dict[str, Any],
        prompts: dict[str, str],
    ) -> WorkerResult:
        """Process a single document and return results.

        Args:
            document_text: Extracted text content of the document.
            criteria: User-provided criteria for this job type.
            prompts: Rendered prompt templates.

        Returns:
            WorkerResult with structured findings.
        """
        ...

    def quality_check(
        self,
        document_text: str,
        initial_result: WorkerResult,
        criteria: dict[str, Any],
        prompts: dict[str, str],
    ) -> QualityCheckResult:
        """Run quality assurance on an initial result.

        Args:
            document_text: Original document text.
            initial_result: The initial worker result to review.
            criteria: User-provided criteria.
            prompts: Rendered prompt templates.

        Returns:
            QualityCheckResult indicating approval or revision.
        """
        ...
