from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from dailyainotes import queue, worker
from dailyainotes.settings import Settings

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_the_worker_creates_its_queue_and_runs_the_daily_edition_at_0130_utc(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs: list[tuple[str | None, bool]] = []

    async def run_editions(settings: Settings, slug: str | None, *, collect: bool) -> list[Any]:
        runs.append((slug, collect))
        return []

    monkeypatch.setattr(worker, "run_editions", run_editions)
    with worker.app.replace_connector(queue.connector(database_url)):
        # The first start creates the queue's tables.
        await worker.run(wait=False)
        async with worker.app.open_async():
            await worker.daily_edition.defer_async(timestamp=0)
        await worker.run(wait=False)

    crons = {p.task.name: p.cron for p in worker.app.periodic_registry.periodic_tasks.values()}
    assert crons == {
        "dailyainotes.worker.daily_edition": "30 1 * * *",
        "dailyainotes.worker.purge_ask_log": "15 0 * * *",
        "dailyainotes.worker.purge_sign_ins": "20 0 * * *",
        "dailyainotes.worker.nightly_eval": "30 4 * * *",
    }
    assert runs == [(None, True)]


async def test_an_accepted_suggestion_queues_one_planner_run_for_the_worker(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    planned: list[str] = []

    @asynccontextmanager
    async def planner(settings: Settings, engine: Any) -> AsyncIterator[None]:
        yield None

    async def plan_topic(engine: Any, graph: Any, slug: str) -> Any:
        planned.append(slug)
        return SimpleNamespace(id=1)

    monkeypatch.setattr(worker.planning, "planner", planner)
    monkeypatch.setattr(worker.planning, "plan_topic", plan_topic)
    send = queue.plan_queue(database_url)  # as the API does
    with worker.app.replace_connector(queue.connector(database_url)):
        await worker.run(wait=False)
        await send("chess")
        await send("chess")  # asked twice before the worker ran: one run
        await worker.run(wait=False)

    assert planned == ["chess"]
