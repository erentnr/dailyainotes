"""Topics readers add (ADR 0006): each is made as a draft topic at once, planned by the worker,
and live for everyone once its plan is approved."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, insert, select

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import Topic, TopicSuggestion
from dailyainotes.domain.accounts import topic_slug


@dataclass(frozen=True)
class ReaderSuggestion:
    id: int
    name: str
    note: str
    status: str
    reason: str
    created_at: datetime
    # The topic made from it, and whether it is active yet.
    topic_slug: str | None
    topic_status: str | None


@dataclass(frozen=True)
class KnownTopic:
    slug: str
    name: str
    description: str


async def planning_count(engine: AsyncEngine, reader_id: int) -> int:
    """The reader's topics still being planned: made, not live yet, not declined."""
    async with engine.connect() as connection:
        count: int = (
            await connection.execute(
                select(func.count())
                .select_from(TopicSuggestion)
                .join(Topic, Topic.id == TopicSuggestion.topic_id)
                .where(
                    TopicSuggestion.reader_id == reader_id,
                    TopicSuggestion.status == "accepted",
                    Topic.status == "draft",
                )
            )
        ).scalar_one()
    return count


async def add(engine: AsyncEngine, reader_id: int, name: str, note: str) -> str:
    """Make the reader's topic as a draft, with a slug no other topic has; the slug."""
    async with engine.begin() as connection:
        taken = set((await connection.execute(select(Topic.slug))).scalars())
        slug = topic_slug(name, taken)
        topic_id = (
            await connection.execute(
                insert(Topic)
                .values(slug=slug, name=name, description=note or name, status="draft")
                .returning(Topic.id)
            )
        ).scalar_one()
        await connection.execute(
            insert(TopicSuggestion).values(
                reader_id=reader_id,
                name=name,
                note=note,
                status="accepted",
                topic_id=topic_id,
                decided_at=func.now(),
            )
        )
    return slug


async def for_reader(engine: AsyncEngine, reader_id: int) -> list[ReaderSuggestion]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(
                TopicSuggestion.id,
                TopicSuggestion.name,
                TopicSuggestion.note,
                TopicSuggestion.status,
                TopicSuggestion.reason,
                TopicSuggestion.created_at,
                Topic.slug,
                Topic.status,
            )
            .outerjoin(Topic, Topic.id == TopicSuggestion.topic_id)
            .where(TopicSuggestion.reader_id == reader_id)
            .order_by(TopicSuggestion.created_at.desc(), TopicSuggestion.id.desc())
        )
        return [ReaderSuggestion(*row) for row in rows]


async def known_topics(engine: AsyncEngine) -> list[KnownTopic]:
    """Topics a new one may duplicate: the active ones, and readers' topics being planned."""
    planning = select(TopicSuggestion.topic_id).where(TopicSuggestion.status == "accepted")
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(Topic.slug, Topic.name, Topic.description)
            .where((Topic.status == "active") | Topic.id.in_(planning))
            .order_by(Topic.slug)
        )
        return [KnownTopic(*row) for row in rows]
