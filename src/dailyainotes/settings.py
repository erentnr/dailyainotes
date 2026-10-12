"""Application settings: the only place that reads the environment.

Every setting here also appears in `.env.example`.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: LogLevel = "INFO"
    database_url: str = "postgresql+psycopg://dan:dan@localhost:5432/dailyainotes"
    # Optional: raises GitHub's API limit from 60 to 5,000 requests an hour.
    github_token: str | None = None
    # Where the local embedding model (64 MB) is downloaded once.
    embedding_cache_dir: str = ".cache/fastembed"

    # Model providers (free plans). Without a key, the router skips that provider.
    ollama_api_key: SecretStr | None = None
    ollama_base_url: str = "https://ollama.com"
    openrouter_api_key: SecretStr | None = None
    # Ollama does not publish its free credits; the router stops at this many tokens a day.
    ollama_daily_token_budget: int = 600_000

    # One chain per role: provider:model pairs, tried in order.
    llm_planner: str = "ollama:gpt-oss:120b,openrouter:google/gemma-4-31b-it:free"

    # Langfuse Cloud tracing; off when the keys are empty. cloud.langfuse.com is the EU region.
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
