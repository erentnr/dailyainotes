"""The FastAPI application. Uvicorn builds it with `create_app` (`--factory`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from dailyainotes.api import health
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
    app.include_router(health.router, prefix="/api/v1")
    return app
