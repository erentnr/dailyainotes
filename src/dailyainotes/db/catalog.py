"""Load the catalog into the database. Adds and updates; never deletes or deactivates."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from dailyainotes.db.publishers import ensure_publisher
from dailyainotes.db.tables import Publisher, Source, Topic, TopicSource


@dataclass(frozen=True)
class PublisherRow:
    domain: str
    name: str
    kind: str
    owner_group: str
    trust_prior: float


@dataclass(frozen=True)
class SourceRow:
    type: str
    locator: str
    config: dict[str, Any]
    publisher_domain: str | None


@dataclass(frozen=True)
class TopicRow:
    slug: str
    name: str
    description: str
    controversial: bool
    sources: list[SourceRow]


@dataclass(frozen=True)
class SyncCounts:
    topics: int
    active_topics: int
    publishers: int
    sources: int


async def sync(
    engine: AsyncEngine, publishers: list[PublisherRow], topics: list[TopicRow]
) -> SyncCounts:
    async with engine.begin() as connection:
        for publisher in publishers:
            values = {
                "name": publisher.name,
                "kind": publisher.kind,
                "owner_group": publisher.owner_group,
                "trust_prior": publisher.trust_prior,
            }
            await connection.execute(
                insert(Publisher)
                .values(domain=publisher.domain, **values)
                .on_conflict_do_update(index_elements=["domain"], set_=values)
            )
        for topic in topics:
            values = {
                "name": topic.name,
                "description": topic.description,
                "controversial": topic.controversial,
            }
            # A topic with catalog sources is active. Without them it keeps whatever status
            # it has, so a topic the Topic Planner activated stays active.
            if topic.sources:
                values["status"] = "active"
            topic_id = (
                await connection.execute(
                    insert(Topic)
                    .values(slug=topic.slug, **values)
                    .on_conflict_do_update(index_elements=["slug"], set_=values)
                    .returning(Topic.id)
                )
            ).scalar_one()
            for source in topic.sources:
                await add_source(connection, topic_id, source)
        counts = (
            await connection.execute(
                select(
                    select(func.count()).select_from(Topic).scalar_subquery(),
                    select(func.count())
                    .select_from(Topic)
                    .where(Topic.status == "active")
                    .scalar_subquery(),
                    select(func.count()).select_from(Publisher).scalar_subquery(),
                    select(func.count()).select_from(Source).scalar_subquery(),
                )
            )
        ).one()
    return SyncCounts(*counts)


async def add_source(connection: AsyncConnection, topic_id: int, source: SourceRow) -> None:
    """Create or update a source and link it to the topic. Shared by the catalog sync and the
    Topic Planner."""
    publisher_id = (
        await ensure_publisher(connection, source.publisher_domain)
        if source.publisher_domain
        else None
    )
    values = {"type": source.type, "config": source.config, "publisher_id": publisher_id}
    source_id = (
        await connection.execute(
            insert(Source)
            .values(locator=source.locator, **values)
            .on_conflict_do_update(index_elements=["locator"], set_=values)
            .returning(Source.id)
        )
    ).scalar_one()
    await connection.execute(
        insert(TopicSource).values(topic_id=topic_id, source_id=source_id).on_conflict_do_nothing()
    )
