from datetime import UTC, datetime

import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.db.ingest import NewDocument, save_document
from dailyainotes.db.tables import Source
from dailyainotes.domain.chunking import heading_chunk
from dailyainotes.ingestion.catalog import Catalog, sync_catalog
from dailyainotes.retrieval.hybrid import hybrid_search
from dailyainotes.sources.urls import url_hash

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

F1_FEED = "https://f1.example.com/feed"
SPACE_FEED = "https://space.example.com/feed"
CORPUS = {
    F1_FEED: [
        ("Late safety car decides a wet race", "A safety car on lap 40 changed the result."),
        ("Team confirms an engine penalty", "A new power unit means a grid drop."),
        ("Rookie impresses in practice", "Fastest in the second session."),
    ],
    SPACE_FEED: [
        ("Comet visible at dawn this week", "Look low in the east before sunrise."),
        ("Crewed launch delayed by weather", "The new window opens tomorrow."),
    ],
}


async def seed(engine: AsyncEngine, embeddings: Embeddings) -> None:
    await sync_catalog(
        engine,
        Catalog.model_validate(
            {
                "topics": [
                    {
                        "slug": "f1",
                        "name": "F1",
                        "description": "d",
                        "sources": [{"type": "rss", "url": F1_FEED}],
                    },
                    {
                        "slug": "space",
                        "name": "Space",
                        "description": "d",
                        "sources": [{"type": "rss", "url": SPACE_FEED}],
                    },
                ]
            }
        ),
    )
    async with engine.connect() as connection:
        source_ids = dict((await connection.execute(select(Source.locator, Source.id))).all())
    for feed, items in CORPUS.items():
        for title, lead in items:
            url = f"{feed.removesuffix('/feed')}/{url_hash(title)[:8]}"
            text = heading_chunk(title, lead)
            await save_document(
                engine,
                NewDocument(
                    url=url,
                    canonical_url_hash=url_hash(url),
                    source_id=source_ids[feed],
                    publisher_id=None,
                    title=title,
                    lead=lead,
                    published_at=datetime(2026, 10, 12, tzinfo=UTC),
                    text_policy="summary",
                    policy_reason="test",
                    content=None,
                    content_purge_after=None,
                ),
                [(text, embeddings.embed_query(text))],
            )


async def test_the_matching_document_ranks_first_in_both_methods(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await seed(engine, embeddings)

    hits = await hybrid_search(engine, embeddings, "safety car")

    top = hits[0]
    assert top.chunk.title == "Late safety car decides a wet race"
    assert (top.full_text_rank, top.vector_rank) == (1, 1)


async def test_vector_search_still_finds_results_when_no_word_matches(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await seed(engine, embeddings)

    hits = await hybrid_search(engine, embeddings, "zzzz unmatched words", limit=3)

    assert len(hits) == 3
    assert all(hit.full_text_rank is None for hit in hits)


async def test_a_topic_filter_keeps_other_topics_out(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await seed(engine, embeddings)

    hits = await hybrid_search(engine, embeddings, "launch window", topic_slugs=["f1"])

    assert hits
    assert all(hit.chunk.url.startswith("https://f1.example.com/") for hit in hits)


async def test_the_limit_caps_the_results(engine: AsyncEngine, embeddings: Embeddings) -> None:
    await seed(engine, embeddings)

    assert len(await hybrid_search(engine, embeddings, "race", limit=2)) == 2
