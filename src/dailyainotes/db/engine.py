"""The async engine the API and the worker share."""

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

log = structlog.get_logger(__name__)


def create_engine(database_url: str) -> AsyncEngine:
    # A short connect timeout keeps the health check from hanging when the database is gone.
    return create_async_engine(
        database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3}
    )


async def database_is_reachable(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        log.warning("database_unreachable", error=str(error))
        return False
    return True
