"""Document-related schemas."""

import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Response for a single document."""

    id: str
    job_id: str
    filename: str
    status: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Response after uploading documents."""

    job_id: str
    uploaded: int
    documents: list[DocumentResponse]
