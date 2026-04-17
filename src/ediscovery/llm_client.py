"""LLM client factory — supports OpenAI and Azure AI Foundry."""

import logging

from openai import AzureOpenAI, OpenAI

from ediscovery.config import ModelConfig, settings

logger = logging.getLogger(__name__)


def create_llm_client(config: ModelConfig) -> OpenAI:
    """Create an LLM client based on the configured provider.

    Args:
        config: Model configuration with retry/timeout settings.

    Returns:
        An OpenAI-compatible client (OpenAI or AzureOpenAI).

    Raises:
        ValueError: If the provider is not supported or misconfigured.
    """
    provider = settings.llm_provider.lower()

    match provider:
        case "azure":
            if not settings.azure_api_key:
                raise ValueError(
                    "AZURE_API_KEY is required when "
                    "LLM_PROVIDER=azure"
                )
            if not settings.azure_endpoint:
                raise ValueError(
                    "AZURE_ENDPOINT is required when "
                    "LLM_PROVIDER=azure"
                )
            logger.info(
                "Using Azure AI Foundry (endpoint=%s)",
                settings.azure_endpoint,
            )
            return AzureOpenAI(
                api_key=settings.azure_api_key,
                azure_endpoint=settings.azure_endpoint,
                api_version=settings.azure_api_version,
                max_retries=config.max_retries,
                timeout=config.timeout,
            )
        case "openai":
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when "
                    "LLM_PROVIDER=openai"
                )
            logger.info("Using OpenAI direct")
            return OpenAI(
                api_key=settings.openai_api_key,
                max_retries=config.max_retries,
                timeout=config.timeout,
            )
        case _:
            raise ValueError(
                f"Unsupported LLM_PROVIDER: '{provider}'. "
                f"Use 'openai' or 'azure'."
            )
