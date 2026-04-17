"""Job type registry for pluggable worker agents."""

import logging
from collections.abc import Callable
from typing import Any

from review.agents.base import JobWorker
from review.config import ModelConfig, get_model_config

logger = logging.getLogger(__name__)


class JobTypeRegistry:
    """Registry mapping job types to their worker classes.

    Use the @register decorator or register_worker() to add new
    job types. The orchestrator looks up workers by job_type string.
    """

    _workers: dict[str, type[Any]] = {}

    @classmethod
    def register(
        cls, job_type: str
    ) -> Callable[[type[Any]], type[Any]]:
        """Decorator to register a worker class for a job type.

        Args:
            job_type: String identifier for the job type.

        Returns:
            Decorator function.
        """
        def decorator(worker_cls: type[Any]) -> type[Any]:
            cls._workers[job_type] = worker_cls
            logger.info(
                "Registered worker %s for job type '%s'",
                worker_cls.__name__,
                job_type,
            )
            return worker_cls
        return decorator

    @classmethod
    def get_worker(
        cls,
        job_type: str,
        model_config: ModelConfig | None = None,
    ) -> JobWorker:
        """Instantiate and return a worker for the given job type.

        Args:
            job_type: The job type to look up.
            model_config: Optional override. Uses per-job-type
                default from config if not provided.

        Returns:
            An instantiated worker.

        Raises:
            ValueError: If no worker is registered for the job type.
        """
        worker_cls = cls._workers.get(job_type)
        if worker_cls is None:
            available = ", ".join(sorted(cls._workers.keys()))
            raise ValueError(
                f"No worker registered for job type '{job_type}'. "
                f"Available: {available}"
            )
        config = model_config or get_model_config(job_type)
        return worker_cls(config)  # type: ignore[return-value]

    @classmethod
    def available_types(cls) -> list[str]:
        """Return list of registered job types."""
        return sorted(cls._workers.keys())
