"""Relevancy review worker agent."""

import json
import logging
from typing import Any

from openai import APIError

from review.agents.base import QualityCheckResult, WorkerResult
from review.agents.registry import JobTypeRegistry
from review.agents.relevancy.prompts import (
    DOCUMENT_PROMPT,
    QUALITY_CHECK_PROMPT,
    SYSTEM_PROMPT,
)
from review.config import ModelConfig
from review.llm_client import create_llm_client

logger = logging.getLogger(__name__)

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "relevancy_review",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_relevant": {"type": "boolean"},
                "tag": {
                    "type": "string",
                    "enum": ["RELEVANT", "NOT_RELEVANT"],
                },
                "matched_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "explanation": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": [
                "is_relevant",
                "tag",
                "matched_criteria",
                "explanation",
                "confidence",
            ],
            "additionalProperties": False,
        },
    },
}

_REVISED_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_relevant": {"type": "boolean"},
        "tag": {
            "type": "string",
            "enum": ["RELEVANT", "NOT_RELEVANT"],
        },
        "matched_criteria": {
            "type": "array",
            "items": {"type": "string"},
        },
        "explanation": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": [
        "is_relevant",
        "tag",
        "matched_criteria",
        "explanation",
        "confidence",
    ],
    "additionalProperties": False,
}

QC_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "quality_check",
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


@JobTypeRegistry.register("relevancy_review")
class RelevancyWorker:
    """Worker agent for document relevancy review."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = create_llm_client(config)
        self._model = config.model

    @property
    def job_type(self) -> str:
        """Return the job type this worker handles."""
        return "relevancy_review"

    def process_document(
        self,
        document_text: str,
        criteria: dict[str, Any],
        prompts: dict[str, str],
    ) -> WorkerResult:
        """Process a document for relevancy review.

        Uses the primary (cheap) model first. If confidence is
        below the threshold and a fallback model is configured,
        escalates to the stronger model automatically.

        Args:
            document_text: Extracted text content of the document.
            criteria: Dict with 'relevant' and 'not_relevant' lists.
            prompts: Prompt templates keyed by name.

        Returns:
            WorkerResult with relevancy determination.
        """
        system_prompt = self._render_prompt(
            prompts.get("system_prompt", SYSTEM_PROMPT),
            criteria,
        )
        user_prompt = prompts.get(
            "document_prompt", DOCUMENT_PROMPT
        ).format(document_text=document_text)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = self._call_review(messages, self._model)

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
            result = self._call_review(
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
        """Run quality assurance on an initial relevancy result.

        Args:
            document_text: Original document text.
            initial_result: The initial worker result to review.
            criteria: User-provided criteria.
            prompts: Prompt templates keyed by name.

        Returns:
            QualityCheckResult indicating approval or revision.
        """
        initial_assessment = json.dumps(
            {
                **initial_result.result_data,
                "confidence": initial_result.confidence,
                "explanation": initial_result.explanation,
            },
            indent=2,
        )

        qc_prompt = prompts.get(
            "quality_check_prompt", QUALITY_CHECK_PROMPT
        ).format(
            relevant_criteria="\n".join(
                f"- {c}" for c in criteria.get("relevant", [])
            ),
            not_relevant_criteria="\n".join(
                f"- {c}"
                for c in criteria.get("not_relevant", [])
            ),
            initial_assessment=initial_assessment,
            document_text=document_text[:5000],
        )

        # QC always uses fallback (stronger) model if available
        qc_model = self._config.fallback_model or self._model
        logger.info("Running quality check via %s", qc_model)

        try:
            response = self._client.chat.completions.create(
                model=qc_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior legal QC reviewer."
                        ),
                    },
                    {"role": "user", "content": qc_prompt},
                ],
                response_format=QC_SCHEMA,
            )
        except APIError as e:
            logger.error(
                "API error during QC: %s", e.message
            )
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
                    "is_relevant": rev["is_relevant"],
                    "tag": rev["tag"],
                    "matched_criteria": rev["matched_criteria"],
                },
                confidence=float(rev["confidence"]),
                explanation=rev["explanation"],
                prompt_tokens=initial_result.prompt_tokens,
                completion_tokens=initial_result.completion_tokens,
            )

        return QualityCheckResult(
            is_approved=is_approved,
            revised_result=revised,
            reason=reason,
        )

    def _call_review(
        self,
        messages: list[dict[str, str]],
        model: str,
    ) -> WorkerResult:
        """Call the LLM for a relevancy review.

        Args:
            messages: Chat messages to send.
            model: Model deployment name to use.

        Returns:
            WorkerResult with parsed response.
        """
        logger.info("Calling %s for relevancy review", model)

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=REVIEW_SCHEMA,
            )
        except APIError as e:
            logger.error("API error during review: %s", e.message)
            raise RuntimeError(
                f"API error: {e.message}"
            ) from e

        content = response.choices[0].message.content or "{}"
        usage = response.usage
        parsed = json.loads(content)

        return WorkerResult(
            is_successful=True,
            result_data={
                "is_relevant": parsed["is_relevant"],
                "tag": parsed["tag"],
                "matched_criteria": parsed["matched_criteria"],
            },
            confidence=float(parsed["confidence"]),
            explanation=parsed["explanation"],
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=(
                usage.completion_tokens if usage else 0
            ),
        )

    def _render_prompt(
        self, template: str, criteria: dict[str, Any]
    ) -> str:
        """Render a prompt template with criteria values."""
        relevant_list = criteria.get("relevant", [])
        not_relevant_list = criteria.get("not_relevant", [])

        return template.format(
            relevant_criteria="\n".join(
                f"- {c}" for c in relevant_list
            ),
            not_relevant_criteria="\n".join(
                f"- {c}" for c in not_relevant_list
            )
            if not_relevant_list
            else "- (none specified)",
        )
