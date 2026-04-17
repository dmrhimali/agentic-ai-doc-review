"""Application configuration via environment variables."""

from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class ModelConfig:
    """LLM configuration for a specific job type.

    Attributes:
        model: Primary model deployment name.
        fallback_model: Stronger model to escalate to when
            confidence is below the threshold. Empty = no fallback.
        confidence_threshold: Escalate to fallback_model if
            the primary model's confidence is below this value.
        max_retries: Retry count for transient API errors.
        timeout: Request timeout in seconds.
    """

    model: str = "gpt-5-nano"
    fallback_model: str = ""
    confidence_threshold: float = 0.7
    max_retries: int = 3
    timeout: float = 120.0


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Tolerate env vars for job types not yet wired into code
        # (e.g. PII_DETECT_*) instead of failing startup.
        extra="ignore",
    )

    # LLM provider: "openai" or "azure"
    llm_provider: str = "azure"

    # OpenAI direct
    openai_api_key: str = ""

    # Azure AI Foundry
    azure_api_key: str = ""
    azure_endpoint: str = ""
    azure_api_version: str = "2024-12-01-preview"

    # Model overrides — set via env vars, applied on top of defaults.
    # Use your Azure deployment names or OpenAI model IDs.
    relevancy_review_model: str = "gpt-5-nano"
    relevancy_review_fallback_model: str = "gpt-5-mini"
    relevancy_review_confidence_threshold: float = 0.7

    entity_extraction_model: str = "gpt-5-nano"
    entity_extraction_fallback_model: str = "gpt-5-mini"
    entity_extraction_confidence_threshold: float = 0.7

    database_url: str = (
        "mysql+pymysql://docreview:docreview@localhost:3306/docreview"
    )

    upload_dir: str = "./uploads"
    log_level: str = "INFO"
    debug: bool = False


settings = Settings()


def _build_model_configs() -> dict[str, ModelConfig]:
    """Build MODEL_CONFIGS from env-driven settings."""
    return {
        "relevancy_review": ModelConfig(
            model=settings.relevancy_review_model,
            fallback_model=settings.relevancy_review_fallback_model,
            confidence_threshold=settings.relevancy_review_confidence_threshold,
            max_retries=3,
            timeout=120.0,
        ),
        "entity_extraction": ModelConfig(
            model=settings.entity_extraction_model,
            fallback_model=settings.entity_extraction_fallback_model,
            confidence_threshold=settings.entity_extraction_confidence_threshold,
            max_retries=3,
            timeout=120.0,
        ),
    }


MODEL_CONFIGS = _build_model_configs()
DEFAULT_MODEL_CONFIG = ModelConfig()


def get_model_config(job_type: str) -> ModelConfig:
    """Get the model configuration for a job type.

    Args:
        job_type: The job type identifier.

    Returns:
        ModelConfig for the job type, or the default.
    """
    return MODEL_CONFIGS.get(job_type, DEFAULT_MODEL_CONFIG)
