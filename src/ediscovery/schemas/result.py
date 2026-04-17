"""Result-related schemas."""

import datetime
from typing import Any

from pydantic import BaseModel


class RelevancyResult(BaseModel):
    """Structured result from relevancy review."""

    is_relevant: bool
    tag: str
    matched_criteria: list[str]
    explanation: str
    confidence: float


class ReviewResultResponse(BaseModel):
    """Response for a single review result."""

    id: str
    job_id: str
    document_id: str
    job_type: str
    result: dict[str, Any]
    confidence: float
    explanation: str
    model_used: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class JobResultsResponse(BaseModel):
    """Response containing all results for a job."""

    job_id: str
    job_type: str
    total: int
    results: list[ReviewResultResponse]


class PromptTemplateResponse(BaseModel):
    """Response for a prompt template."""

    id: int
    job_type: str
    name: str
    version: int
    content: str
    is_active: bool

    model_config = {"from_attributes": True}


class PromptUpdateRequest(BaseModel):
    """Request to update a prompt template."""

    content: str
