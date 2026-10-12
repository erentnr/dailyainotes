"""The FastAPI application. Uvicorn builds it with `create_app` (`--factory`)."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from dailyainotes.api import ask, health
from dailyainotes.db.engine import create_engine
from dailyainotes.logging import configure_logging
from dailyainotes.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # Here, not in the lifespan: uvicorn calls the factory before its first log line.
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_engine(settings.database_url)
        yield
        await app.state.engine.dispose()

    app = FastAPI(title="Daily AI Notes", version=version("dailyainotes"), lifespan=lifespan)
    app.state.settings = settings
    app.state.ask_deps = None
    key = settings.ip_hash_key
    app.state.ip_key = key.get_secret_value().encode() if key else secrets.token_bytes(32)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(ask.router, prefix="/api/v1")
    return app
