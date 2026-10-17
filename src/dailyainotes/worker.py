"""The worker runs the queue (`queue.py`): every active topic's edition at 01:30 UTC, the eval
set with its judge at 04:30, the Ask-log purge at 00:15 and expired sign-in codes and sessions
at 00:20, and the Topic Planner whenever the editor accepts a topic suggestion.

Start it with `dan-worker`, not `python -m`, which would build a second app in `__main__` that
the worker cannot find its tasks in.
"""

import asyncio
from datetime import UTC, datetime

import procrastinate
import structlog

from dailyainotes.accounts import purge_expired
from dailyainotes.ask import purge
from dailyainotes.db.engine import create_engine
from dailyainotes.evals import run_eval
from dailyainotes.graphs import planning
from dailyainotes.graphs.edition import run_editions
from dailyainotes.llm.embeddings import LocalEmbeddings
from dailyainotes.logging import configure_logging
from dailyainotes.queue import app
from dailyainotes.settings import get_settings

log = structlog.get_logger(__name__)


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


@app.periodic(cron="15 0 * * *")
@app.task(queueing_lock="purge")
async def purge_ask_log(timestamp: int) -> None:
    """The Ask log after 30 days, rate-limit counts after a day (INTENT.md)."""
    engine = create_engine(get_settings().database_url)
    try:
        await purge(engine, datetime.now(UTC))
    finally:
        await engine.dispose()


@app.periodic(cron="20 0 * * *")
@app.task(queueing_lock="purge-sign-ins")
async def purge_sign_ins(timestamp: int) -> None:
    """Expired sign-in codes and sessions (ADR 0003)."""
    engine = create_engine(get_settings().database_url)
    try:
        await purge_expired(engine, datetime.now(UTC))
    finally:
        await engine.dispose()


# Queued by /admin when the editor accepts a suggestion (queue.PLAN_TOPIC names it). A retry is
# safe: a failed plan saved no proposal.
@app.task(retry=procrastinate.RetryStrategy(max_attempts=2, wait=600))
async def plan_topic(slug: str) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        embeddings = LocalEmbeddings(settings.embedding_cache_dir)
        async with planning.planner(settings, engine, embeddings) as graph:
            proposal = await planning.plan_topic(engine, graph, slug)
        log.info("topic_planned", topic=slug, proposal=proposal.id)
    finally:
        await engine.dispose()


# 04:30, not 04:00: the server reboots at 04:00 UTC when a security update needs it.
@app.periodic(cron="30 4 * * *")
@app.task(queueing_lock="eval")
async def nightly_eval(timestamp: int) -> None:
    """The eval set with the Ask model and the judge, after the daily edition is done."""
    metrics, _ = await run_eval(get_settings(), judge=True, record=True)
    log.info("eval", **metrics)


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
