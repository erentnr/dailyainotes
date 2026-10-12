"""Langfuse Cloud tracing for every model call, when its keys are set; nothing otherwise."""

from langchain_core.callbacks import BaseCallbackHandler
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

from dailyainotes.settings import Settings


def tracing_callbacks(settings: Settings) -> list[BaseCallbackHandler]:
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return []
    # Creating the client registers it; the callback finds it by public key.
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        base_url=settings.langfuse_base_url,
    )
    return [CallbackHandler(public_key=settings.langfuse_public_key)]


def flush_tracing(settings: Settings) -> None:
    """Send buffered traces before a short-lived process (the CLI) exits."""
    if settings.langfuse_public_key:
        get_client(public_key=settings.langfuse_public_key).flush()
