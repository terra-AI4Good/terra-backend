"""LLM provider configuration."""

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for a single model call."""

    model: str = Field(
        default="gpt-4o-mini",
        description="LiteLLM model identifier (e.g. 'gpt-4o')",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    timeout: float = Field(default=60.0, gt=0, description="Request timeout in seconds")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    stream: bool = False


class LLMSettings(BaseModel):
    """Global LLM settings loaded from environment."""

    default_model: str = "gpt-4o-mini"
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    default_timeout: float = 60.0

    # Provider API keys (resolved from env at runtime)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    azure_api_key: str | None = None
    azure_api_base: str | None = None
    azure_api_version: str | None = None
