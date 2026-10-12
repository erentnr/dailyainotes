"""What ingestion reads and writes. A document and its chunks are saved in one transaction."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.publishers import ensure_publisher
from dailyainotes.db.tables import Chunk, Document, Publisher, Source, Topic, TopicSource


@dataclass(frozen=True)
class SourceRecord:
    id: int
    type: str
    locator: str
    config: dict[str, Any]
    etag: str | None
    last_modified: str | None
    publisher_id: int | None


@dataclass(frozen=True)
class PublisherRef:
    id: int
    paywalled: bool


@dataclass(frozen=True)
class NewDocument:
    url: str
    canonical_url_hash: str
    source_id: int
    publisher_id: int | None
    title: str
    lead: str
    published_at: datetime | None
    text_policy: str
    policy_reason: str
    content: str | None
    content_purge_after: datetime | None


async def active_topic_slugs(engine: AsyncEngine) -> list[str]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(Topic.slug).where(Topic.status == "active").order_by(Topic.slug)
        )
        return list(rows.scalars())


async def sources_for_topic(engine: AsyncEngine, slug: str) -> list[SourceRecord]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(
                Source.id,
                Source.type,
                Source.locator,
                Source.config,
                Source.etag,
                Source.last_modified,
                Source.publisher_id,
            )
            .join(TopicSource, TopicSource.source_id == Source.id)
            .join(Topic, Topic.id == TopicSource.topic_id)
            .where(Topic.slug == slug, Source.status == "active")
            .order_by(Source.id)
        )
        return [SourceRecord(*row) for row in rows]


async def record_fetch(
    engine: AsyncEngine,
    source_id: int,
    *,
    etag: str | None,
    last_modified: str | None,
    at: datetime,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(etag=etag, last_modified=last_modified, last_fetched_at=at, error_streak=0)
        )


async def record_failure(engine: AsyncEngine, source_id: int, *, at: datetime) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(error_streak=Source.error_streak + 1, last_fetched_at=at)
        )


async def known_hashes(engine: AsyncEngine, hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(Document.canonical_url_hash).where(Document.canonical_url_hash.in_(hashes))
        )
        return set(rows.scalars())


async def publisher_for(engine: AsyncEngine, domain: str) -> PublisherRef:
    async with engine.begin() as connection:
        publisher_id = await ensure_publisher(connection, domain)
        paywalled = (
            await connection.execute(
                select(Publisher.paywalled).where(Publisher.id == publisher_id)
            )
        ).scalar_one()
    return PublisherRef(publisher_id, paywalled)


async def save_document(
    engine: AsyncEngine, document: NewDocument, chunks: list[tuple[str, list[float]]]
) -> int | None:
    """The new document's id, or None when another run saved the same URL first."""
    async with engine.begin() as connection:
        document_id = (
            await connection.execute(
                insert(Document)
                .values(**document.__dict__)
                .on_conflict_do_nothing(index_elements=["canonical_url_hash"])
                .returning(Document.id)
            )
        ).scalar_one_or_none()
        if document_id is None:
            return None
        await connection.execute(
            insert(Chunk),
            [
                {"document_id": document_id, "ordinal": ordinal, "text": text, "embedding": vector}
                for ordinal, (text, vector) in enumerate(chunks)
            ],
        )
    return document_id


async def purge_expired_content(engine: AsyncEngine, *, now: datetime) -> int:
    """Drop page text past its retention date: the content and every chunk but the heading."""
    async with engine.begin() as connection:
        expired = (
            select(Document.id)
            .where(Document.content_purge_after <= now, Document.content.is_not(None))
            .scalar_subquery()
        )
        await connection.execute(
            delete(Chunk).where(Chunk.document_id.in_(expired), Chunk.ordinal > 0)
        )
        result = await connection.execute(
            update(Document)
            .where(Document.content_purge_after <= now, Document.content.is_not(None))
            .values(content=None)
        )
    return result.rowcount
