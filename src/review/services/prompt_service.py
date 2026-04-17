"""Prompt template CRUD and rendering service."""

import logging

from sqlalchemy.orm import Session

from review.models.prompt import PromptTemplate

logger = logging.getLogger(__name__)


def get_active_prompts(
    db: Session, job_type: str
) -> list[PromptTemplate]:
    """Get all active prompt templates for a job type.

    Args:
        db: Database session.
        job_type: The job type to filter by.

    Returns:
        List of active PromptTemplate rows.
    """
    return (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.job_type == job_type,
            PromptTemplate.is_active.is_(True),
        )
        .all()
    )


def get_prompt_by_id(
    db: Session, prompt_id: int
) -> PromptTemplate | None:
    """Get a prompt template by ID.

    Args:
        db: Database session.
        prompt_id: The prompt template ID.

    Returns:
        PromptTemplate if found, None otherwise.
    """
    return (
        db.query(PromptTemplate)
        .filter(PromptTemplate.id == prompt_id)
        .first()
    )


def update_prompt_content(
    db: Session, prompt_id: int, content: str
) -> PromptTemplate | None:
    """Update the content of a prompt template.

    Args:
        db: Database session.
        prompt_id: The prompt template ID to update.
        content: New prompt content.

    Returns:
        Updated PromptTemplate if found, None otherwise.
    """
    prompt = get_prompt_by_id(db, prompt_id)
    if prompt is None:
        return None

    prompt.content = content
    db.commit()
    db.refresh(prompt)
    logger.info("Updated prompt template %d", prompt_id)
    return prompt
