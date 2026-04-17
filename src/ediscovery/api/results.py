"""Results and prompts API endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ediscovery.database import get_db
from ediscovery.schemas.result import (
    JobResultsResponse,
    PromptTemplateResponse,
    PromptUpdateRequest,
    ReviewResultResponse,
)
from ediscovery.services import job_service, prompt_service

router = APIRouter(prefix="/api/v1", tags=["results"])


@router.get(
    "/jobs/{job_id}/results",
    response_model=JobResultsResponse,
)
def get_job_results(
    job_id: str, db: Session = Depends(get_db)
) -> JobResultsResponse:
    """Get all results for a job."""
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    results = job_service.get_job_results(db, job_id)

    result_responses: list[ReviewResultResponse] = []
    for r in results:
        result_data: dict[str, Any]
        if isinstance(r.result, str):
            result_data = json.loads(r.result)
        else:
            result_data = r.result  # type: ignore[assignment]

        result_responses.append(
            ReviewResultResponse(
                id=r.id,
                job_id=r.job_id,
                document_id=r.document_id,
                job_type=r.job_type,
                result=result_data,
                confidence=float(r.confidence),
                explanation=r.explanation,
                model_used=r.model_used,
                prompt_tokens=r.prompt_tokens,
                completion_tokens=r.completion_tokens,
                created_at=r.created_at,
            )
        )

    return JobResultsResponse(
        job_id=job_id,
        job_type=job.job_type,
        total=len(result_responses),
        results=result_responses,
    )


@router.get(
    "/prompts/{job_type}",
    response_model=list[PromptTemplateResponse],
)
def get_prompts(
    job_type: str, db: Session = Depends(get_db)
) -> list[PromptTemplateResponse]:
    """Get active prompts for a job type."""
    prompts = prompt_service.get_active_prompts(db, job_type)
    return [
        PromptTemplateResponse.model_validate(p) for p in prompts
    ]


@router.put(
    "/prompts/{prompt_id}",
    response_model=PromptTemplateResponse,
)
def update_prompt(
    prompt_id: int,
    body: PromptUpdateRequest,
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    """Update a prompt template's content."""
    prompt = prompt_service.update_prompt_content(
        db, prompt_id, body.content
    )
    if prompt is None:
        raise HTTPException(
            status_code=404, detail="Prompt not found"
        )
    return PromptTemplateResponse.model_validate(prompt)
