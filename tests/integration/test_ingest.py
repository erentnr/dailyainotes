from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.db.ingest import purge_expired_content
from dailyainotes.db.tables import Chunk, Document, Source
from dailyainotes.ingestion.catalog import Catalog, sync_catalog
from dailyainotes.ingestion.run import ingest_topic

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

NOW = datetime(2026, 10, 12, 18, tzinfo=UTC)
FEED = "https://news.example.com/feed/"
ARXIV = "https://export.arxiv.org/api/query"
HTML = {"Content-Type": "text/html"}
CATALOG = Catalog.model_validate(
    {
        "topics": [
            {
                "slug": "demo",
                "name": "Demo",
                "description": "d",
                "sources": [
                    {"type": "rss", "url": FEED},
                    {"type": "arxiv", "query": 'abs:"open-weight"'},
                ],
            }
        ]
    }
)


def site(fixture: Callable[[str], bytes]) -> dict[str, Any]:
    return {
        FEED: fixture("rss/feed.xml"),
        ARXIV: fixture("arxiv/query.xml"),
        "https://news.example.com/robots.txt": (404, b"", {}),
        "https://news.example.com/2026/10/12/": (200, fixture("pages/article.html"), HTML),
        "https://news.example.com/2026/10/11/": (200, fixture("pages/meta-noai.html"), HTML),
        "https://news.example.com/2026/10/10/": (200, fixture("pages/thin.html"), HTML),
    }


async def ingest(engine: AsyncEngine, web: Any, embeddings: Embeddings, now: datetime) -> Any:
    return await ingest_topic(
        engine=engine, http=web.http, embeddings=embeddings, slug="demo", now=now
    )


async def test_items_are_saved_with_their_text_policy_and_chunks(
    engine: AsyncEngine,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    embeddings: Embeddings,
) -> None:
    await sync_catalog(engine, CATALOG)

    feed, arxiv = await ingest(engine, web(site(fixture)), embeddings, NOW)

    assert [(d.text_policy, d.reason) for d in feed.saved] == [
        ("full", "allowed"),
        ("link_only", "meta robots: noai"),
        ("summary", "too little article text"),
    ]
    assert len(arxiv.saved) == 3
    assert {d.text_policy for d in arxiv.saved} == {"summary"}
    async with engine.connect() as connection:
        rows = (
            await connection.execute(
                select(Document.text_policy, Document.content_purge_after, func.count(Chunk.id))
                .join(Chunk, Chunk.document_id == Document.id)
                .group_by(Document.id)
                .order_by(Document.id)
            )
        ).all()
    full = rows[0]
    assert full.text_policy == "full"
    assert full.content_purge_after == NOW + timedelta(days=30)
    assert full[2] > 1
    assert all(row[2] == 1 for row in rows[1:])


async def test_a_second_run_saves_nothing_twice_and_asks_conditionally(
    engine: AsyncEngine,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    embeddings: Embeddings,
) -> None:
    await sync_catalog(engine, CATALOG)
    first = site(fixture)
    first[FEED] = (200, fixture("rss/feed.xml"), {"ETag": '"v1"'})
    await ingest(engine, web(first), embeddings, NOW)

    second = web(site(fixture) | {FEED: (304, b"", {})})
    feed, arxiv = await ingest(engine, second, embeddings, NOW)

    assert feed.not_modified
    assert feed.saved == []
    assert arxiv.saved == []
    feed_request = next(r for r in second.requests if str(r.url) == FEED)
    assert feed_request.headers["If-None-Match"] == '"v1"'


async def test_items_already_saved_are_not_fetched_again(
    engine: AsyncEngine,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    embeddings: Embeddings,
) -> None:
    await sync_catalog(engine, CATALOG)
    await ingest(engine, web(site(fixture)), embeddings, NOW)

    again = web(site(fixture))
    feed, _ = await ingest(engine, again, embeddings, NOW)

    assert feed.fetched == 3
    assert feed.saved == []
    assert {str(r.url) for r in again.requests} == {FEED, ARXIV + again_query(again)}


def again_query(recorded: Any) -> str:
    arxiv_url = next(str(r.url) for r in recorded.requests if str(r.url).startswith(ARXIV))
    return arxiv_url.removeprefix(ARXIV)


async def test_a_failing_source_is_counted_and_the_others_still_run(
    engine: AsyncEngine,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    embeddings: Embeddings,
) -> None:
    await sync_catalog(engine, CATALOG)

    feed, arxiv = await ingest(engine, web(site(fixture) | {FEED: (500, b"", {})}), embeddings, NOW)

    assert feed.error is not None
    assert len(arxiv.saved) == 3
    async with engine.connect() as connection:
        streak = (
            await connection.execute(select(Source.error_streak).where(Source.locator == FEED))
        ).scalar_one()
    assert streak == 1


async def test_page_text_is_purged_after_thirty_days(
    engine: AsyncEngine,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    embeddings: Embeddings,
) -> None:
    await sync_catalog(engine, CATALOG)
    await ingest(engine, web(site(fixture)), embeddings, NOW)

    purged = await purge_expired_content(engine, now=NOW + timedelta(days=31))

    assert purged == 1
    async with engine.connect() as connection:
        content = await connection.execute(
            select(func.count()).where(Document.content.is_not(None))
        )
        extra_chunks = await connection.execute(select(func.count()).where(Chunk.ordinal > 0))
    assert content.scalar_one() == 0
    assert extra_chunks.scalar_one() == 0
