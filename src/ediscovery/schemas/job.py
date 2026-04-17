"""Job-related request and response schemas."""

import datetime
from typing import Any

from pydantic import BaseModel, Field

JOB_TYPE_PATTERN = r"^(relevancy_review|entity_extraction)$"


class RelevancyCriteria(BaseModel):
    """User-provided criteria for relevancy review."""

    relevant: list[str] = Field(
        ...,
        description="Criteria that make a document relevant.",
    )
    not_relevant: list[str] = Field(
        default_factory=list,
        description="Criteria that make a document not relevant.",
    )


class EntityExtractionCriteria(BaseModel):
    """User-provided criteria for entity extraction."""

    entity_types: list[str] = Field(
        default_factory=list,
        description=(
            "Entity types to extract (e.g. person, organization, "
            "amount, date, clause). Empty list = extract all default "
            "types."
        ),
    )


class JobCreate(BaseModel):
    """Request to create a new job."""

    job_type: str = Field(
        ...,
        pattern=JOB_TYPE_PATTERN,
        description="Type of job to run.",
    )
    criteria: dict[str, Any] = Field(
        ...,
        description=(
            "Job-specific criteria. Shape depends on job_type — see "
            "RelevancyCriteria or EntityExtractionCriteria."
        ),
    )


class JobCreateFromDirectory(BaseModel):
    """Request to create and run a job from a local directory."""

    job_type: str = Field(
        ...,
        pattern=JOB_TYPE_PATTERN,
        description="Type of job to run.",
    )
    criteria: dict[str, Any] = Field(
        ...,
        description=(
            "Job-specific criteria. Shape depends on job_type."
        ),
    )
    document_directory: str = Field(
        ...,
        description="Path to local directory containing documents.",
    )


class JobResponse(BaseModel):
    """Job status response."""

    id: str
    job_type: str
    status: str
    criteria: str
    total_documents: int
    processed_documents: int
    created_at: datetime.datetime
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: list[JobResponse]
    total: int
