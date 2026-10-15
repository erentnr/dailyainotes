"""The task queue: Procrastinate on the same Postgres, so there is no broker. The worker runs
the tasks; the API puts work on the queue by task name, so it never imports the worker.

Its tables live in the `procrastinate` schema (migration 0005), outside what the drift test
compares; the worker creates them on its first start.
"""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

import procrastinate
from procrastinate.exceptions import AlreadyEnqueued

from dailyainotes.db.checkpoints import libpq_url
from dailyainotes.settings import get_settings

PLAN_TOPIC = "dailyainotes.worker.plan_topic"


def connector(database_url: str, **pool: Any) -> procrastinate.PsycopgConnector:
    return procrastinate.PsycopgConnector(
        conninfo=libpq_url(database_url), kwargs={"options": "-c search_path=procrastinate"}, **pool
    )


# Connects only when opened; tests swap the database with `app.replace_connector`.
app = procrastinate.App(connector=connector(get_settings().database_url))


async def queue_plan(slug: str) -> None:
    """Ask the worker to run the Topic Planner for a topic. The app must be open; a request for
    a topic already waiting in the queue changes nothing."""
    with suppress(AlreadyEnqueued):
        await app.configure_task(PLAN_TOPIC, queueing_lock=f"plan:{slug}").defer_async(slug=slug)


def plan_queue(database_url: str) -> Callable[[str], Awaitable[None]]:
    """`queue_plan` for the API: it opens the queue for each request, with one connection, so
    the API starts and reports its health whether or not the database is up."""
    lock = asyncio.Lock()

    async def queue(slug: str) -> None:
        async with lock:
            with app.replace_connector(connector(database_url, min_size=1, max_size=1)):
                async with app.open_async():
                    await queue_plan(slug)

    return queue
