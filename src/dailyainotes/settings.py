"""Application settings: the only place that reads the environment.

Every setting here also appears in `.env.example`.
"""

from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
