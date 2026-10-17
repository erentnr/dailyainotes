"""The FastAPI application. Uvicorn builds it with `create_app` (`--factory`)."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from starlette.routing import Route

from dailyainotes import queue
from dailyainotes.api import accounts, admin, ask, health, mcp_server, notes
from dailyainotes.api.access import access_verifier
from dailyainotes.db.engine import create_engine
from dailyainotes.external.http import create_client
from dailyainotes.logging import configure_logging
from dailyainotes.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # Here, not in the lifespan: uvicorn calls the factory before its first log line.
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_engine(settings.database_url)
        # Accepted topic suggestions ask the worker for a Topic Planner run.
        app.state.plan_queue = queue.plan_queue(settings.database_url)
        async with create_client() as client, app.state.mcp.session_manager.run():
            app.state.accounts = accounts.account_deps(settings, app.state.engine, client)
            yield
        await app.state.engine.dispose()

    app = FastAPI(title="Daily AI Notes", version=version("dailyainotes"), lifespan=lifespan)
    app.state.settings = settings
    app.state.models = None
    key = settings.ip_hash_key
    app.state.ip_key = key.get_secret_value().encode() if key else secrets.token_bytes(32)
    team, audience = settings.cf_access_team_domain, settings.cf_access_aud
    app.state.access = access_verifier(team, audience) if team and audience else None
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(ask.router, prefix="/api/v1")
    app.include_router(notes.router, prefix="/api/v1")
    app.include_router(accounts.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1/admin")
    # A plain route, not in the OpenAPI schema: MCP clients speak JSON-RPC to it (ADR 0005).
    app.state.mcp = mcp_server.build(app.state)
    app.router.routes.append(Route(mcp_server.PATH, mcp_server.Endpoint(app.state, app.state.mcp)))
    return app
