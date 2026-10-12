"""The worker: Procrastinate, on the same Postgres, runs every active topic's edition at
01:30 UTC. Start it with `dan-worker`; not `python -m`, which would build a second app in
`__main__` that the worker cannot find its tasks in.

Its tables live in the `procrastinate` schema (migration 0005), outside what the drift test
compares; the worker creates them on its first start.
"""

import asyncio

import procrastinate
import structlog

from dailyainotes.db.checkpoints import libpq_url
from dailyainotes.graphs.edition import run_editions
from dailyainotes.logging import configure_logging
from dailyainotes.settings import get_settings

log = structlog.get_logger(__name__)


def connector(database_url: str) -> procrastinate.PsycopgConnector:
    return procrastinate.PsycopgConnector(
        conninfo=libpq_url(database_url), kwargs={"options": "-c search_path=procrastinate"}
    )


# Connects only when opened; tests swap the database with `app.replace_connector`.
app = procrastinate.App(connector=connector(get_settings().database_url))


@app.periodic(cron="30 1 * * *")
# A retry is safe: a done edition is skipped and a story resumes from its checkpoint.
@app.task(queueing_lock="daily", retry=procrastinate.RetryStrategy(max_attempts=2, wait=900))
async def daily_edition(timestamp: int) -> None:
    for report in await run_editions(get_settings(), None, collect=True):
        log.info(
            "edition",
            topic=report.slug,
            status=report.status,
            collected=report.collected,
            stories=report.stories,
            waiting=len(report.waiting),
            errors=report.errors,
        )


async def run(*, wait: bool = True) -> None:
    """Work through the queue; with `wait=False`, stop once it is empty (for tests)."""
    async with app.open_async():
        if not await app.check_connection_async():
            await app.schema_manager.apply_schema_async()
        # One job at a time: Ollama's free plan allows one request at a time.
        await app.run_worker_async(concurrency=1, wait=wait)


def main() -> None:
    configure_logging(get_settings().log_level)
    asyncio.run(run())
