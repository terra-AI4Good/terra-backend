"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Terra"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    # Database
    database_url: str = f"sqlite+aiosqlite:///{Path('terra.db').resolve()}"

    # Security
    secret_key: str = "change-me-in-production"  # noqa: S105
    allowed_origins: list[str] = ["http://localhost:3000"]

    # LLM / LiteLLM
    llm_default_model: str = "gpt-4o-mini"
    llm_default_temperature: float = 0.7
    llm_default_max_tokens: int = 4096
    llm_default_timeout: float = 60.0

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    azure_api_key: str | None = None
    azure_api_base: str | None = None
    azure_api_version: str | None = None

    # Tools / External services
    search_api_key: str | None = None
    search_api_provider: str = "tavily"
    tavily_api_key: str | None = None
    tavily_search_depth: str = "basic"
    tavily_default_max_results: int = 5
    tavily_timeout_seconds: float = 20.0

    # BA Jobsuche API
    ba_jobs_base_url: str = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
    ba_jobs_api_key: str = "jobboerse-jobsuche"
    ba_jobs_default_radius_km: int = 50
    ba_jobs_default_size: int = 10
    ba_jobs_fetch_details_limit: int = 5


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
