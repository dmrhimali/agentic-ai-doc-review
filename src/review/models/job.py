"""Job and JobDocument ORM models."""

import datetime
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from review.models.base import Base


class Job(Base):
    """Top-level job tracking."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending", "running", "completed", "completed_with_errors", "failed",
            name="job_status",
        ),
        default="pending",
        nullable=False,
    )
    criteria: Mapped[str] = mapped_column(Text, nullable=False)
    total_documents: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    processed_documents: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    documents: Mapped[list["JobDocument"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobDocument(Base):
    """Documents belonging to a job."""

    __tablename__ = "job_documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending", "processing", "completed", "failed",
            name="document_status",
        ),
        default="pending",
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    job: Mapped["Job"] = relationship(back_populates="documents")
