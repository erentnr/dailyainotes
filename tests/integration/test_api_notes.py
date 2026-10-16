from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.api.app import create_app
from dailyainotes.ask import AskDeps
from dailyainotes.db.tables import Topic
from dailyainotes.evals import EVALS, CorpusNote, load_corpus, read_jsonl
from dailyainotes.ingestion.catalog import load_catalog, sync_catalog
from dailyainotes.settings import Settings

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

# Ten fictional notes: climate tech (2026-09-02 to 09-30) and astronomy (09-03 to 10-01).
NOTES = read_jsonl(EVALS / "corpus.jsonl", CorpusNote)[:10]


@pytest.fixture
async def site(engine: AsyncEngine, embeddings: Embeddings) -> AsyncIterator[httpx2.AsyncClient]:
    """The API over the ten notes, published and on active topics."""
    await load_corpus(engine, AskDeps(engine, embeddings, None), NOTES)  # type: ignore[arg-type]
    async with engine.begin() as connection:
        await connection.execute(update(Topic).values(status="active"))
    app = create_app(Settings(_env_file=None))
    app.state.engine = engine  # ASGITransport does not run the lifespan
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def get(site: httpx2.AsyncClient, path: str) -> Any:
    response = await site.get(path)
    assert response.status_code == 200, response.text
    return response.json()


async def test_topics_list_the_active_ones_with_their_note_counts(
    site: httpx2.AsyncClient,
) -> None:
    topics = await get(site, "/api/v1/topics")

    assert [(t["slug"], t["notes"]) for t in topics] == [
        ("astronomy-and-spaceflight", 5),
        ("climate-tech", 5),
    ]


async def test_topics_carry_their_category_from_the_catalog(
    site: httpx2.AsyncClient, engine: AsyncEngine
) -> None:
    before = await get(site, "/api/v1/topics")
    await sync_catalog(engine, load_catalog())
    after = await get(site, "/api/v1/topics")

    assert [t["category"] for t in before] == [None, None]
    assert {t["slug"]: t["category"] for t in after}["climate-tech"] == "climate"


async def test_the_daily_page_shows_the_latest_day_with_notes_on_the_picked_topics(
    site: httpx2.AsyncClient,
) -> None:
    climate = await get(site, "/api/v1/notes?topic=climate-tech")
    either = await get(site, "/api/v1/notes?topic=climate-tech&topic=astronomy-and-spaceflight")
    chosen_day = await get(site, "/api/v1/notes?date=2026-09-03")

    assert climate["date"] == "2026-09-30"
    (note,) = climate["notes"]
    assert note["title"] == "Verdant Fuels opens a solar-powered hydrogen plant in Port Ellis"
    assert "[1]" not in note["summary"]
    # The corpus's stories merge no reports of their own; a card says how many it merged.
    assert note["reports"] == 0
    assert either["date"] == "2026-10-01"
    assert [n["topic"] for n in chosen_day["notes"]] == ["astronomy-and-spaceflight"]


async def test_a_note_and_a_topic_timeline_are_found_by_slug(
    site: httpx2.AsyncClient,
) -> None:
    slug = NOTES[0].slug
    note = await get(site, f"/api/v1/notes/{slug}")
    timeline = await get(site, "/api/v1/topics/climate-tech/notes?before=2026-09-20")

    assert note["body"].endswith("[1][2].")
    assert note["citations"] == []
    assert [n["edition_date"] for n in timeline["notes"]] == [
        "2026-09-16",
        "2026-09-09",
        "2026-09-02",
    ]
    missing = await site.get("/api/v1/notes/no-such-note")
    unknown_topic = await site.get("/api/v1/topics/knitting/notes")
    assert (missing.status_code, unknown_topic.status_code) == (404, 404)


async def test_stats_count_what_exists_and_the_last_fourteen_days(
    site: httpx2.AsyncClient,
) -> None:
    stats = await get(site, "/api/v1/stats")

    assert stats["totals"]["notes_published"] == 10
    assert stats["totals"]["topics_active"] == 2
    assert len(stats["days"]) == 14
    assert stats["days"][-1]["date"] == datetime.now(UTC).date().isoformat()


async def test_stats_show_nothing_internal(site: httpx2.AsyncClient) -> None:
    """No cost, model use, model names, eval scores or index sizes: they are ours, not readers'."""
    stats = await get(site, "/api/v1/stats")

    assert set(stats) == {"totals", "days"}
    assert set(stats["totals"]) == {"notes_published", "topics_active", "documents"}
    assert set(stats["days"][-1]) == {"date", "notes"}
