"""The async engine the API and the worker share."""

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Re-exported: services pass the engine around without importing SQLAlchemy themselves.
from sqlalchemy.ext.asyncio import AsyncEngine as AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine

log = structlog.get_logger(__name__)


def create_engine(database_url: str) -> AsyncEngine:
    # A short connect timeout keeps the health check from hanging when the database is gone.
    # Error messages leave out bound values (emails, questions), since errors reach the logs.
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
        hide_parameters=True,
    )


async def database_is_reachable(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        log.warning("database_unreachable", error=str(error))
        return False
    return True
