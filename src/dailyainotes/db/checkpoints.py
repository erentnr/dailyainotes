"""LangGraph's Postgres checkpointer, in its own `langgraph` schema (migration 0003).

It needs psycopg 3 connections with autocommit (its setup creates indexes concurrently),
no prepared statements, and dict rows.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url


def libpq_url(database_url: str) -> str:
    """`postgresql+psycopg://…` (SQLAlchemy) → `postgresql://…` (libpq)."""
    return make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)


@asynccontextmanager
async def checkpointer(database_url: str) -> AsyncIterator[AsyncPostgresSaver]:
    async with await AsyncConnection.connect(
        libpq_url(database_url),
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        options="-c search_path=langgraph",
    ) as connection:
        saver = AsyncPostgresSaver(connection)
        await saver.setup()
        yield saver
