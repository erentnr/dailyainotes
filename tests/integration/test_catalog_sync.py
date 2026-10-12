import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.db.tables import Publisher, Source, Topic
from dailyainotes.ingestion.catalog import Catalog, load_catalog, sync_catalog

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_syncing_the_catalog_twice_changes_nothing(engine: AsyncEngine) -> None:
    first = await sync_catalog(engine, load_catalog())
    second = await sync_catalog(engine, load_catalog())

    assert first == second
    assert first.topics == 12
    assert first.active_topics == 2


async def test_sync_never_demotes_a_topic_activated_elsewhere(engine: AsyncEngine) -> None:
    await sync_catalog(engine, load_catalog())
    async with engine.begin() as connection:
        await connection.execute(
            update(Topic).where(Topic.slug == "tennis").values(status="active")
        )

    await sync_catalog(engine, load_catalog())

    async with engine.connect() as connection:
        status = (
            await connection.execute(select(Topic.status).where(Topic.slug == "tennis"))
        ).scalar_one()
    assert status == "active"


async def test_a_source_from_an_unlisted_domain_gets_an_unknown_publisher(
    engine: AsyncEngine,
) -> None:
    catalog = Catalog.model_validate(
        {
            "topics": [
                {
                    "slug": "demo",
                    "name": "Demo",
                    "description": "d",
                    "sources": [{"type": "rss", "url": "https://news.example.org/feed"}],
                }
            ]
        }
    )

    await sync_catalog(engine, catalog)

    async with engine.connect() as connection:
        publisher = (
            await connection.execute(
                select(Publisher.kind, Publisher.trust_prior)
                .join(Source, Source.publisher_id == Publisher.id)
                .where(Source.locator == "https://news.example.org/feed")
            )
        ).one()
    assert publisher == ("unknown", 0.5)
