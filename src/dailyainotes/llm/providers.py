"""Build chat models from `provider:model` refs, and the router from settings."""

from collections.abc import Callable

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from dailyainotes.llm.router import DailyLimit, Ledger, ModelRef, Router, parse_chain
from dailyainotes.llm.tracing import tracing_callbacks
from dailyainotes.settings import Settings

# OpenRouter's free models allow 50 requests a day without a credit purchase (checked
# 2026-10-12). The owner chose not to buy credits.
OPENROUTER_FREE_REQUESTS_PER_DAY = 50


class MissingKeyError(Exception):
    pass


def model_factory(settings: Settings) -> Callable[[ModelRef], BaseChatModel]:
    def make(ref: ModelRef) -> BaseChatModel:
        match ref.provider:
            case "ollama":
                if not settings.ollama_api_key:
                    raise MissingKeyError("OLLAMA_API_KEY is not set")
                key = settings.ollama_api_key.get_secret_value()
                model = init_chat_model(
                    f"ollama:{ref.model}",
                    base_url=settings.ollama_base_url,
                    client_kwargs={"headers": {"Authorization": f"Bearer {key}"}},
                    temperature=0,
                )
            case "openrouter":
                if not settings.openrouter_api_key:
                    raise MissingKeyError("OPENROUTER_API_KEY is not set")
                model = init_chat_model(
                    f"openrouter:{ref.model}",
                    api_key=settings.openrouter_api_key.get_secret_value(),
                    temperature=0,
                    # INTENT.md: no provider that collects or trains on prompts.
                    openrouter_provider={"data_collection": "deny"},
                )
            case _:
                raise ValueError(f"unknown provider {ref.provider!r}")
        return model

    return make


def build_router(settings: Settings, ledger: Ledger) -> Router:
    return Router(
        {
            "planner": parse_chain(settings.llm_planner),
            "researcher": parse_chain(settings.llm_researcher),
            "writer": parse_chain(settings.llm_writer),
            "extractor": parse_chain(settings.llm_extractor),
            "verifier": parse_chain(settings.llm_verifier),
            "ask": parse_chain(settings.llm_ask),
            "judge": parse_chain(settings.llm_judge),
        },
        model_factory(settings),
        ledger,
        limits={
            "ollama": DailyLimit(tokens=settings.ollama_daily_token_budget),
            "openrouter": DailyLimit(requests=OPENROUTER_FREE_REQUESTS_PER_DAY),
        },
        callbacks=tracing_callbacks(settings),
    )
