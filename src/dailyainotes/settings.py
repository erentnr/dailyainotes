"""Application settings: the only place that reads the environment.

Every setting here also appears in `.env.example`.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    # An invalid setting is reported without its value, which may be a secret.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

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
    llm_researcher: str = "ollama:gpt-oss:120b,openrouter:google/gemma-4-31b-it:free"
    llm_writer: str = "ollama:gpt-oss:120b,openrouter:google/gemma-4-31b-it:free"
    llm_extractor: str = "ollama:gpt-oss:20b,openrouter:google/gemma-4-31b-it:free"
    # From another model family than the Writer's, so it does not share the Writer's mistakes.
    llm_verifier: str = "ollama:gemma4:31b,openrouter:google/gemma-4-31b-it:free"
    # Ollama only: OpenRouter's 50 free requests a day go to the pipeline (INTENT.md).
    llm_ask: str = "ollama:gpt-oss:120b"
    # The nightly eval's judge, from another family than the models it judges.
    llm_judge: str = "ollama:gemma4:31b"

    # The /admin page's bearer token (INTENT.md); admin is off while it is empty.
    admin_token: SecretStr | None = None

    # Keys the hash of a visitor's IP address for Ask's rate limits. Without it, a random key
    # is made at start, and the limits reset whenever the API restarts.
    ip_hash_key: SecretStr | None = None

    # The deployed commit, kept with eval runs; Compose sets it from the image tag.
    git_sha: str = ""

    # Langfuse Cloud tracing; off when the keys are empty. cloud.langfuse.com is the EU region.
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

    @model_validator(mode="after")
    def langfuse_keys_in_place(self) -> Settings:
        public = self.langfuse_public_key or ""
        secret = self.langfuse_secret_key.get_secret_value() if self.langfuse_secret_key else ""
        if public.startswith("sk-lf-") or secret.startswith("pk-lf-"):
            # Langfuse then answers every trace with a bare 401.
            raise ValueError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY look swapped")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
