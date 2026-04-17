"""Seed default prompt templates into the database."""

import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy.orm import Session

from review.agents.entity_extraction.prompts import (
    DOCUMENT_PROMPT as ENTITY_DOCUMENT_PROMPT,
)
from review.agents.entity_extraction.prompts import (
    QUALITY_CHECK_PROMPT as ENTITY_QUALITY_CHECK_PROMPT,
)
from review.agents.entity_extraction.prompts import (
    SYSTEM_PROMPT as ENTITY_SYSTEM_PROMPT,
)
from review.agents.relevancy.prompts import (
    DOCUMENT_PROMPT,
    QUALITY_CHECK_PROMPT,
    SYSTEM_PROMPT,
)
from review.database import SessionLocal, engine
from review.models.base import Base
from review.models.prompt import PromptTemplate

SEED_PROMPTS = [
    {
        "job_type": "relevancy_review",
        "name": "system_prompt",
        "version": 1,
        "content": SYSTEM_PROMPT,
    },
    {
        "job_type": "relevancy_review",
        "name": "document_prompt",
        "version": 1,
        "content": DOCUMENT_PROMPT,
    },
    {
        "job_type": "relevancy_review",
        "name": "quality_check_prompt",
        "version": 1,
        "content": QUALITY_CHECK_PROMPT,
    },
    {
        "job_type": "entity_extraction",
        "name": "system_prompt",
        "version": 1,
        "content": ENTITY_SYSTEM_PROMPT,
    },
    {
        "job_type": "entity_extraction",
        "name": "document_prompt",
        "version": 1,
        "content": ENTITY_DOCUMENT_PROMPT,
    },
    {
        "job_type": "entity_extraction",
        "name": "quality_check_prompt",
        "version": 1,
        "content": ENTITY_QUALITY_CHECK_PROMPT,
    },
]


def seed(db: Session) -> None:
    """Insert default prompts if they don't already exist."""
    for prompt_data in SEED_PROMPTS:
        existing = (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.job_type == prompt_data["job_type"],
                PromptTemplate.name == prompt_data["name"],
                PromptTemplate.version == prompt_data["version"],
            )
            .first()
        )
        if existing is None:
            prompt = PromptTemplate(**prompt_data)
            db.add(prompt)
            print(
                f"  + {prompt_data['job_type']}/{prompt_data['name']} "
                f"v{prompt_data['version']}"
            )
        else:
            print(
                f"  = {prompt_data['job_type']}/{prompt_data['name']} "
                f"v{prompt_data['version']} (exists)"
            )

    db.commit()


def main() -> None:
    """Create tables and seed prompts."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    print("Seeding prompt templates...")
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    main()
