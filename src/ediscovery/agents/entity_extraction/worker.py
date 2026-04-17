"""Entity extraction worker agent."""

import json
import logging
from typing import Any

from openai import APIError

from ediscovery.agents.base import QualityCheckResult, WorkerResult
from ediscovery.agents.entity_extraction.prompts import (
    DEFAULT_ENTITY_TYPES,
    DOCUMENT_PROMPT,
    QUALITY_CHECK_PROMPT,
    SYSTEM_PROMPT,
)
from ediscovery.agents.registry import JobTypeRegistry
from ediscovery.config import ModelConfig
from ediscovery.llm_client import create_llm_client

logger = logging.getLogger(__name__)

_ENTITY_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "value": {"type": "string"},
        "context": {"type": "string"},
    },
    "required": ["type", "value", "context"],
    "additionalProperties": False,
}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "entity_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": _ENTITY_ITEM_SCHEMA,
                },
                "summary": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["entities", "summary", "confidence"],
            "additionalProperties": False,
        },
    },
}

_REVISED_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": _ENTITY_ITEM_SCHEMA,
        },
        "summary": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["entities", "summary", "confidence"],
    "additionalProperties": False,
}

QC_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "entity_extraction_qc",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_approved": {"type": "boolean"},
                "reason": {"type": "string"},
                "revised_result": {
                    "anyOf": [
                        _REVISED_RESULT_SCHEMA,
                        {"type": "null"},
                    ],
                },
            },
            "required": [
                "is_approved",
                "reason",
                "revised_result",
            ],
            "additionalProperties": False,
        },
    },
}


@JobTypeRegistry.register("entity_extraction")
class EntityExtractionWorker:
    """Worker agent for structured entity extraction."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = create_llm_client(config)
        self._model = config.model

    @property
    def job_type(self) -> str:
        """Return the job type this worker handles."""
        return "entity_extraction"

    def process_document(
        self,
        document_text: str,
        criteria: dict[str, Any],
        prompts: dict[str, str],
    ) -> WorkerResult:
        """Extract entities from a document.

        Uses the primary (cheap) model first. If confidence is
        below the threshold and a fallback model is configured,
        escalates to the stronger model automatically.

        Args:
            document_text: Extracted text content of the document.
            criteria: Dict with optional 'entity_types' list.
                Empty or missing = use DEFAULT_ENTITY_TYPES.
            prompts: Prompt templates keyed by name.

        Returns:
            WorkerResult with extracted entities.
        """
        entity_types = self._resolve_entity_types(criteria)
        system_prompt = prompts.get(
            "system_prompt", SYSTEM_PROMPT
        ).format(entity_types=self._format_types(entity_types))
        user_prompt = prompts.get(
            "document_prompt", DOCUMENT_PROMPT
        ).format(document_text=document_text)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = self._call_extraction(messages, self._model)

        if (
            result.confidence < self._config.confidence_threshold
            and self._config.fallback_model
        ):
            logger.info(
                "Confidence %.2f < threshold %.2f, "
                "escalating to %s",
                result.confidence,
                self._config.confidence_threshold,
                self._config.fallback_model,
            )
            result = self._call_extraction(
                messages, self._config.fallback_model
            )

        return result

    def quality_check(
        self,
        document_text: str,
        initial_result: WorkerResult,
        criteria: dict[str, Any],
        prompts: dict[str, str],
    ) -> QualityCheckResult:
        """Run quality assurance on an initial extraction.

        Args:
            document_text: Original document text.
            initial_result: The initial worker result to review.
            criteria: User-provided criteria.
            prompts: Prompt templates keyed by name.

        Returns:
            QualityCheckResult indicating approval or revision.
        """
        entity_types = self._resolve_entity_types(criteria)

        initial_assessment = json.dumps(
            {
                **initial_result.result_data,
                "confidence": initial_result.confidence,
                "summary": initial_result.explanation,
            },
            indent=2,
        )

        qc_prompt = prompts.get(
            "quality_check_prompt", QUALITY_CHECK_PROMPT
        ).format(
            entity_types=self._format_types(entity_types),
            initial_assessment=initial_assessment,
            document_text=document_text[:5000],
        )

        qc_model = self._config.fallback_model or self._model
        logger.info("Running quality check via %s", qc_model)

        try:
            response = self._client.chat.completions.create(
                model=qc_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior QC reviewer "
                            "for information extraction."
                        ),
                    },
                    {"role": "user", "content": qc_prompt},
                ],
                response_format=QC_SCHEMA,
            )
        except APIError as e:
            logger.error("API error during QC: %s", e.message)
            raise RuntimeError(
                f"API error during QC: {e.message}"
            ) from e

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        is_approved: bool = parsed["is_approved"]
        reason: str = parsed["reason"]

        revised: WorkerResult | None = None
        if not is_approved and parsed.get("revised_result"):
            rev = parsed["revised_result"]
            revised = WorkerResult(
                is_successful=True,
                result_data={
                    "entities": rev["entities"],
                    "entity_counts": self._count_by_type(
                        rev["entities"]
                    ),
                },
                confidence=float(rev["confidence"]),
                explanation=rev["summary"],
                prompt_tokens=initial_result.prompt_tokens,
                completion_tokens=initial_result.completion_tokens,
            )

        return QualityCheckResult(
            is_approved=is_approved,
            revised_result=revised,
            reason=reason,
        )

    def _call_extraction(
        self,
        messages: list[dict[str, str]],
        model: str,
    ) -> WorkerResult:
        """Call the LLM to extract entities.

        Args:
            messages: Chat messages to send.
            model: Model deployment name to use.

        Returns:
            WorkerResult with parsed extraction.
        """
        logger.info("Calling %s for entity extraction", model)

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=EXTRACTION_SCHEMA,
            )
        except APIError as e:
            logger.error(
                "API error during extraction: %s", e.message
            )
            raise RuntimeError(
                f"API error: {e.message}"
            ) from e

        content = response.choices[0].message.content or "{}"
        usage = response.usage
        parsed = json.loads(content)

        entities = parsed["entities"]

        return WorkerResult(
            is_successful=True,
            result_data={
                "entities": entities,
                "entity_counts": self._count_by_type(entities),
            },
            confidence=float(parsed["confidence"]),
            explanation=parsed["summary"],
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=(
                usage.completion_tokens if usage else 0
            ),
        )

    @staticmethod
    def _resolve_entity_types(
        criteria: dict[str, Any],
    ) -> list[str]:
        """Return configured entity types or defaults."""
        requested = criteria.get("entity_types") or []
        return list(requested) if requested else list(
            DEFAULT_ENTITY_TYPES
        )

    @staticmethod
    def _format_types(entity_types: list[str]) -> str:
        """Render entity types as a bulleted list for prompts."""
        return "\n".join(f"- {t}" for t in entity_types)

    @staticmethod
    def _count_by_type(
        entities: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Count entities grouped by type."""
        counts: dict[str, int] = {}
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            counts[entity_type] = counts.get(entity_type, 0) + 1
        return counts
