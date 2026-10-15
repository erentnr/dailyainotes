from typing import Any

import pytest

from dailyainotes import worker
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
    with worker.app.replace_connector(worker.connector(database_url)):
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
