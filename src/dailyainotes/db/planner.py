"""Topic Planner proposals: saved while the graph waits, then approved or rejected."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from dailyainotes.db.catalog import SourceRow, add_source
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import Topic, TopicProfile


@dataclass(frozen=True)
class TopicRecord:
    id: int
    slug: str
    name: str
    description: str
    status: str


@dataclass(frozen=True)
class Proposal:
    id: int
    slug: str
    version: int
    status: str
    profile: dict[str, Any]
    thread_id: str
    created_at: datetime


async def topic(engine: AsyncEngine, slug: str) -> TopicRecord | None:
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                select(Topic.id, Topic.slug, Topic.name, Topic.description, Topic.status).where(
                    Topic.slug == slug
                )
            )
        ).one_or_none()
    return TopicRecord(*row) if row else None


async def draft_topic_slugs(engine: AsyncEngine) -> list[str]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(Topic.slug).where(Topic.status == "draft").order_by(Topic.slug)
        )
        return list(rows.scalars())


async def next_version(engine: AsyncEngine, topic_id: int) -> int:
    async with engine.connect() as connection:
        latest = (
            await connection.execute(
                select(func.max(TopicProfile.version)).where(TopicProfile.topic_id == topic_id)
            )
        ).scalar_one()
    return (latest or 0) + 1


async def save_proposal(
    engine: AsyncEngine, topic_id: int, version: int, profile: dict[str, Any], thread_id: str
) -> int:
    """Idempotent: a graph that re-runs this step updates the same proposal."""
    async with engine.begin() as connection:
        proposal_id: int = (
            await connection.execute(
                insert(TopicProfile)
                .values(topic_id=topic_id, version=version, profile=profile, thread_id=thread_id)
                .on_conflict_do_update(
                    index_elements=["topic_id", "version"], set_={"profile": profile}
                )
                .returning(TopicProfile.id)
            )
        ).scalar_one()
    return proposal_id


async def proposals(engine: AsyncEngine, *, status: str | None = None) -> list[Proposal]:
    statement = (
        select(
            TopicProfile.id,
            Topic.slug,
            TopicProfile.version,
            TopicProfile.status,
            TopicProfile.profile,
            TopicProfile.thread_id,
            TopicProfile.created_at,
        )
        .join(Topic, Topic.id == TopicProfile.topic_id)
        .order_by(TopicProfile.id)
    )
    if status:
        statement = statement.where(TopicProfile.status == status)
    async with engine.connect() as connection:
        return [Proposal(*row) for row in await connection.execute(statement)]


async def approve(engine: AsyncEngine, proposal_id: int, comment: str) -> None:
    """Add the proposed sources, activate the topic and mark the proposal approved."""
    async with engine.begin() as connection:
        topic_id, profile = (
            await connection.execute(
                select(TopicProfile.topic_id, TopicProfile.profile).where(
                    TopicProfile.id == proposal_id
                )
            )
        ).one()
        for source in profile["sources"]:
            await add_source(
                connection,
                topic_id,
                SourceRow(
                    type=source["type"],
                    locator=source["locator"],
                    config=source["config"],
                    publisher_domain=source["publisher_domain"],
                ),
            )
        await connection.execute(update(Topic).where(Topic.id == topic_id).values(status="active"))
        await decide(connection, proposal_id, "approved", comment)


async def reject(engine: AsyncEngine, proposal_id: int, comment: str) -> None:
    async with engine.begin() as connection:
        await decide(connection, proposal_id, "rejected", comment)


async def decide(connection: AsyncConnection, proposal_id: int, status: str, comment: str) -> None:
    await connection.execute(
        update(TopicProfile)
        .where(TopicProfile.id == proposal_id)
        .values(status=status, decision_comment=comment, decided_at=func.now())
    )
